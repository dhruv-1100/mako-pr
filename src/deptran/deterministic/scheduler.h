#pragma once

#include "../paxos/server.h"
#include "../paxos/coordinator.h"
#include <condition_variable>

namespace janus {

class SchedulerDeterministic : public PaxosServer {
public:
  SchedulerDeterministic();
  virtual ~SchedulerDeterministic() {}

  void Execute(Tx &txn_box, innid_t inn_id) override;
  int Next(int slot_id, shared_ptr<Marshallable> cmd) override;
  bool Dispatch(cmdid_t cmd_id, shared_ptr<Marshallable> cmd, TxnOutput& ret_output) override;
  void OnCommit(const slotid_t slot_id, const ballot_t ballot, shared_ptr<Marshallable> &cmd) override;

protected:
  // Queue to hold transactions that are ready to be executed but waiting for
  // their turn
  map<int, shared_ptr<Marshallable>> pending_txns_;
  int next_slot_to_execute_ = 1;
  int next_slot_to_assign_ = 1;

  void ExecuteNext();
  
  CoordinatorMultiPaxos* paxos_coord_ = nullptr;
  
  struct PendingRequest {
      std::shared_ptr<IntEvent> event;
      TxnOutput output;
  };
  
  std::map<cmdid_t, PendingRequest> pending_requests_;
  std::recursive_mutex mtx_pending_;
};

} // namespace janus
