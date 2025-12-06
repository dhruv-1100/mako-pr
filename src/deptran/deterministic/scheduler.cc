#include "scheduler.h"
#include "../executor.h"
#include "../marshal-value.h"
#include "../tx.h"
#include "../txn_reg.h"

namespace janus {

SchedulerDeterministic::SchedulerDeterministic() : PaxosServer() {
  app_next_ = [this](int slot, shared_ptr<Marshallable> cmd) -> int {
    std::lock_guard<std::recursive_mutex> lock(mtx_pending_);
    pending_txns_[slot] = cmd;
    ExecuteNext();
    return 0;
  };
}

void SchedulerDeterministic::OnCommit(const slotid_t slot_id,
                                    const ballot_t ballot,
                                    shared_ptr<Marshallable> &cmd) {
  std::lock_guard<std::recursive_mutex> lock(mtx_pending_);
  Log_info("SchedulerDeterministic::OnCommit slot %d", slot_id);
  PaxosServer::OnCommit(slot_id, ballot, cmd);
}

void SchedulerDeterministic::Execute(Tx &txn_box, innid_t inn_id) {
  TxLogServer::Execute(txn_box, inn_id);
}

bool SchedulerDeterministic::Dispatch(cmdid_t cmd_id,
                                      shared_ptr<Marshallable> cmd,
                                      TxnOutput &ret_output) {
  fprintf(stderr, "SchedulerDeterministic::Dispatch cmd_id: %lu\n", cmd_id);
  auto vpd = dynamic_pointer_cast<VecPieceData>(cmd);
  int slot_id = 0;
  if (vpd && vpd->sp_vec_piece_data_ && vpd->sp_vec_piece_data_->size() > 0) {
    auto& piece = vpd->sp_vec_piece_data_->at(0);
    if (piece) {
        slot_id = (int)piece->timestamp_;
    } else {
        fprintf(stderr, "Dispatch: piece at 0 is null\n");
    }
  }
  fprintf(stderr, "SchedulerDeterministic::Dispatch slot_id=%d\n", slot_id);

  if (slot_id == 0) {
    Log_info("SchedulerDeterministic::Dispatch: partition_id_=%d, loc_id_=%d",
             partition_id_, loc_id_);
    // Case 1: New Request (Sequencer only)
    // Case 1: New Request (Sequencer only)
    if (partition_id_ == 0 && loc_id_ == 0) {
      int n_replicas = Config::GetConfig()->GetPartitionSize(partition_id_);
      std::set<parid_t> partitions;
      fprintf(stderr, "Dispatch: vpd check\n");
      if (vpd && vpd->sp_vec_piece_data_) {
        int idx = 0;
        fprintf(stderr, "Dispatch: vpd=%p, vec_size=%d\n", vpd.get(), (int)vpd->sp_vec_piece_data_->size());
        for (auto& sp_piece : *vpd->sp_vec_piece_data_) {
           if (sp_piece) {
             fprintf(stderr, "Dispatch: piece %d, addr=%p\n", idx, sp_piece.get());
             partitions.insert(sp_piece->PartitionId());
             fprintf(stderr, "Dispatch: piece %d inserted\n", idx);
           } else {
             fprintf(stderr, "Dispatch: sp_piece at index %d is null\n", idx);
           }
           idx++;
        }
      } else {
        fprintf(stderr, "Dispatch: vpd is null or sp_vec_piece_data_ is null\n");
      }
      Log_info("SchedulerDeterministic::Dispatch: partition_id_=%d, loc_id_=%d, n_replicas=%d, n_partitions=%d",
               partition_id_, loc_id_, n_replicas, (int)partitions.size());
      fprintf(stderr, "DEBUG: n_replicas=%d, partitions.size()=%d\n", n_replicas, (int)partitions.size());
      
      if (n_replicas > 1 || partitions.size() > 1) {
        fprintf(stderr, "DEBUG: Taking MULTI-NODE path (Paxos)\n");
        // Create a new coordinator for each request to avoid concurrency issues
        auto paxos_coord = new CoordinatorMultiPaxos(
            0, Config::GetConfig()->benchmark(), nullptr, 0);
        paxos_coord->par_id_ = partition_id_;
        paxos_coord->partitions_ = partitions;
        paxos_coord->loc_id_ = loc_id_;
        paxos_coord->frame_ = frame_;
        paxos_coord->commo_ = commo_;
        Log_info("SchedulerDeterministic::Dispatch created local paxos_coord");

        // Assign the next slot for this transaction
        int assigned_slot = get_open_slot();
        paxos_coord->set_slot(assigned_slot);

        Log_info("Paxos Submit for slot %d, cmd_id %lu", assigned_slot, cmd_id);

        auto event = Reactor::CreateSpEvent<IntEvent>();
        {
          std::lock_guard<std::recursive_mutex> lock(mtx_pending_);
          pending_requests_[cmd_id].event = event;
          // Pre-store the cmd so OnCommit -> app_next_ can find it
          pending_txns_[assigned_slot] = cmd;
        }

        // Submit to Paxos. The callback is empty because ExecuteNext will 
        // signal completion after transaction execution, not just consensus.
        paxos_coord->Submit(cmd, [this]() { 
          this->ExecuteNext();
        });

        // Wait for ExecuteNext to complete and signal via event->Set(1)
        event->Wait();

        {
          std::lock_guard<std::recursive_mutex> lock(mtx_pending_);
          ret_output = pending_requests_[cmd_id].output;
          pending_requests_.erase(cmd_id);
        }
        event.reset();
        cmd.reset();
        Log_info("SchedulerDeterministic::Dispatch returning true for cmd_id %lu", cmd_id);
        delete paxos_coord;
        return true;
      } else {
        // Single-node: Use simple sequential slot assignment
        // This avoids the blocking issue in single-node setup
        fprintf(stderr, "DEBUG: Taking SINGLE-NODE path (sequential)\n");
        int assigned_slot;
        {
          std::lock_guard<std::recursive_mutex> lock(mtx_pending_);
          assigned_slot = next_slot_to_assign_++;
          pending_txns_[assigned_slot] = cmd;

          // Store the event for this request
          auto event = Reactor::CreateSpEvent<IntEvent>();
          pending_requests_[cmd_id].event = event;
        }

        Log_info("Assigned slot %d to cmd_id %lu", assigned_slot, cmd_id);

        // Set timestamp for the pieces
        if (vpd) {
          for (auto &piece : *vpd->sp_vec_piece_data_) {
            piece->timestamp_ = assigned_slot;
          }
        }

        // Execute the transaction
        ExecuteNext();

        // Wait for completion
        {
          std::unique_lock<std::recursive_mutex> lock(mtx_pending_);
          auto it = pending_requests_.find(cmd_id);
          if (it != pending_requests_.end()) {
            auto event = it->second.event;
            lock.unlock(); // Release lock before waiting
            event->Wait();
            lock.lock();
            ret_output = pending_requests_[cmd_id].output;
            pending_requests_.erase(cmd_id);
          }
        }
        return true;
      }
    } else {
      // Not Sequencer Leader, reject or forward?
      return false;
    }
  } else {
    // Case 2: Ordered Request (Worker)
    Log_info("Dispatch: Worker case, slot_id=%d, cmd_id=%lu", slot_id, cmd_id);
    auto event = Reactor::CreateSpEvent<IntEvent>();
    {
      std::lock_guard<std::recursive_mutex> lock(mtx_pending_);
      pending_requests_[cmd_id].event = event;
      pending_txns_[slot_id] = cmd;
    }
    ExecuteNext();

    Log_info("Dispatch: Worker waiting for event");
    event->Wait();
    Log_info("Dispatch: Worker event signaled");

    {
      std::lock_guard<std::recursive_mutex> lock(mtx_pending_);
      ret_output = pending_requests_[cmd_id].output;
      pending_requests_.erase(cmd_id);
    }
    return true;
  }
}

int SchedulerDeterministic::Next(int slot_id, shared_ptr<Marshallable> cmd) {
  // Receive ordered transaction from the sequencing layer (Paxos)
  // This is only called on the Sequencer (and replicas)
  std::lock_guard<std::recursive_mutex> lock(mtx_pending_);
  pending_txns_[slot_id] = cmd;
  ExecuteNext();
  return 0;
}

void SchedulerDeterministic::ExecuteNext() {
  std::lock_guard<std::recursive_mutex> lock(mtx_pending_);
  Log_info("SchedulerDeterministic::ExecuteNext next_slot: %d, pending_txns_.count=%d",
           next_slot_to_execute_, (int)pending_txns_.count(next_slot_to_execute_));

  while (pending_txns_.count(next_slot_to_execute_)) {
    Log_info("ExecuteNext: entering while loop for slot %d", next_slot_to_execute_);
    auto cmd = pending_txns_[next_slot_to_execute_];
    auto vpd = dynamic_pointer_cast<VecPieceData>(cmd);
    Log_info("ExecuteNext: vpd=%p", (void*)vpd.get());

    if (vpd) {
      cmdid_t cmd_id = vpd->sp_vec_piece_data_->at(0)->root_id_;
      TxnOutput local_output;

      // 1. Execute local pieces
      // Create Tx and Executor
      // We use a simplified execution flow here

      // Start MDB Txn
      mdb::Txn *mdb_txn = mdb_txn_mgr_->start(
          next_slot_to_execute_); // Use slot_id as txn_id for simplicity?
      // Or use cmd_id? cmd_id is better for uniqueness across clients.
      // But slot_id is deterministic.

      // Let's use cmd_id for the Tx object, but we need to ensure deterministic
      // behavior. Mako uses 2PL/OCC usually, but here we are serial.

      // Create a temporary Tx object to hold workspace
      auto tx = make_shared<Tx>(0, cmd_id, this);
      tx->mdb_txn_ = mdb_txn;
      tx->txn_reg_ = txn_reg_;

      bool execute_success = true;
      Log_info("ExecuteNext: Starting piece execution loop. partition_id_=%d", partition_id_);
      int pieces_executed = 0;
      for (auto &piece : *vpd->sp_vec_piece_data_) {
        if (piece->PartitionId() == partition_id_) {
          // Execute piece
          Log_info("ExecuteNext: Executing piece type=%d, inn_id=%d", piece->type_, piece->inn_id());
          auto roottype = piece->root_type_;
          auto subtype = piece->type_;
          TxnPieceDef &piece_def = txn_reg_->get(roottype, subtype);

          int ret_code;
          piece->input.Aggregate(tx->ws_);

          // Execute
          piece_def.proc_handler_(nullptr, *tx, *piece, &ret_code,
                                  local_output[piece->inn_id()]);

          tx->ws_.insert(local_output[piece->inn_id()]);
          pieces_executed++;
        }
      }
      Log_info("ExecuteNext: Finished piece execution loop. Executed %d pieces. Committing mdb_txn.", pieces_executed);

      // Commit MDB Txn
      mdb_txn->commit();
      Log_info("ExecuteNext: mdb_txn committed.");
      delete mdb_txn;
      Log_info("ExecuteNext: mdb_txn deleted.");
      tx->mdb_txn_ = nullptr;

      // 2. If Sequencer Leader, forward to other partitions and aggregate
      if (partition_id_ == 0 && loc_id_ == 0) {
        // Set Slot ID for the pieces if not set (it should be set if we came
        // from Next) But vpd is shared_ptr, so modifying it affects the one in
        // pending_txns_.
        for (auto &piece : *vpd->sp_vec_piece_data_) {
          piece->timestamp_ = next_slot_to_execute_;
        }

        map<parid_t, shared_ptr<vector<shared_ptr<TxPieceData>>>> partitions;
        for (auto &piece : *vpd->sp_vec_piece_data_) {
          if (piece->PartitionId() != partition_id_) {
            if (partitions.find(piece->PartitionId()) == partitions.end()) {
              partitions[piece->PartitionId()] =
                  make_shared<vector<shared_ptr<TxPieceData>>>();
            }
            partitions[piece->PartitionId()]->push_back(piece);
          }
        }

        // Send to other partitions
        // We need to wait for them.
        // Using a counter/barrier.
        // Use IntEvent for waiting in coroutine
        auto agg_event = Reactor::CreateSpEvent<IntEvent>();
        auto sp_pending_replies =
            std::make_shared<std::atomic<int>>(partitions.size());
        std::mutex mtx_agg; // Keep mutex for aggregated_output protection
        TxnOutput aggregated_output = local_output; // Keep aggregated_output

        if (partitions.empty()) {
          // No other partitions to wait for, signal immediately
          Log_info("ExecuteNext: no other partitions, signaling immediately");
          agg_event->Set(1);
        } else {
          Log_info("ExecuteNext: Broadcasting Dispatch to %d partitions", (int)partitions.size());
          for (auto &pair : partitions) {
            Log_info("ExecuteNext: Sending Dispatch to partition %d", pair.first);
            commo()->BroadcastDispatch(
                pair.second, nullptr,
                [&mtx_agg, agg_event, sp_pending_replies,
                 &aggregated_output, pair](int res, TxnOutput &output) {
                  Log_info("ExecuteNext: Received Dispatch reply from partition %d, res=%d, output_size=%d", pair.first, res, (int)output.size());
                  std::lock_guard<std::mutex> lk(mtx_agg);
                  for (auto &op : output) {
                    aggregated_output[op.first] = op.second;
                  }
                  if (sp_pending_replies->fetch_sub(1) == 1) {
                    Log_info("ExecuteNext: All partitions replied, signaling agg_event");
                    agg_event->Set(1);
                  }
                });
          }
        }

        Log_info("ExecuteNext: Waiting for agg_event");
        agg_event->Wait();
        Log_info("ExecuteNext: agg_event signaled");

        // Signal completion to the waiting Dispatch (New Request)
        // Signal completion to the waiting Dispatch (New Request)
        if (pending_requests_.count(cmd_id)) {
          pending_requests_[cmd_id].output = aggregated_output;
          pending_requests_[cmd_id].event->Set(1);
        }
      } else {
          // Worker: Signal completion to the waiting Dispatch (Ordered Request)
          if (pending_requests_.count(cmd_id)) {
            Log_info("ExecuteNext: Worker signaling completion for cmd_id %lu", cmd_id);
            pending_requests_[cmd_id].output = local_output;
            pending_requests_[cmd_id].event->Set(1);
          } else {
             Log_info("ExecuteNext: Worker cmd_id %lu not found in pending_requests_", cmd_id);
          }
      }

      pending_txns_.erase(next_slot_to_execute_);
      next_slot_to_execute_++;
    }
  }

} // namespace janus
}
