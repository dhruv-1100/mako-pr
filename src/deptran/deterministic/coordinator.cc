#include "coordinator.h"
#include "../frame.h"
#include "../communicator.h"
#include "../procedure.h"
#include "../command.h"

namespace janus {

CoordinatorDeterministic::CoordinatorDeterministic(
    uint32_t coo_id, int32_t benchmark, ClientControlServiceImpl *ccsi,
    uint32_t thread_id)
    : Coordinator(coo_id, benchmark, ccsi, thread_id) {}

void CoordinatorDeterministic::DoTxAsync(TxRequest &req) {
  Log_info("CoordinatorDeterministic::DoTxAsync start");
  // 1. Create TxData from request
  auto txn_reg = txn_reg_;
  if (!frame_) {
      Log_fatal("frame_ is null");
  }
  TxData* tx_data = frame_->CreateTxnCommand(req, txn_reg);
  Log_info("TxData created");
  
  // 2. Get all pieces
  // GetReadyPiecesData returns map<parid_t, vector<shared_ptr<SimpleCommand>>>
  // We want ALL pieces.
  auto ready_pieces = tx_data->GetReadyPiecesData();
  
  // 3. Bundle into one VecPieceData
  shared_ptr<vector<shared_ptr<TxPieceData>>> all_pieces = make_shared<vector<shared_ptr<TxPieceData>>>();
  
  for (auto& pair : ready_pieces) {
    for (auto& piece : pair.second) {
      all_pieces->push_back(piece);
    }
  }
  Log_info("Pieces bundled: %d", all_pieces->size());
  
  // 4. Send to Sequencer (Partition 0)
  auto comm = commo_;
  if (!comm) {
      Log_fatal("commo_ is null");
  }
  auto pair_leader_proxy = comm->LeaderProxyForPartition(0); // Sequencer is Partition 0
  auto proxy = pair_leader_proxy.second;
  if (!proxy) {
      Log_fatal("proxy for partition 0 is null");
  }
  
  shared_ptr<VecPieceData> sp_vpd(new VecPieceData);
  sp_vpd->sp_vec_piece_data_ = all_pieces;
  MarshallDeputy md(sp_vpd);
  
  auto callback = req.callback_;
  
  rrr::FutureAttr fuattr;
  fuattr.callback = [this, tx_data, callback](Future* fu) {
    Log_info("CoordinatorDeterministic::DoTxAsync callback");
    int32_t ret;
    TxnOutput outputs;
    fu->get_reply() >> ret >> outputs;
    
    // Handle output
    // We need to pass the output back to the client callback.
    // TxData has the callback.
    
    TxReply reply;
    reply.res_ = ret;
    for (auto& pair : outputs) {
        reply.output_.insert(pair.second.begin(), pair.second.end());
    }
    reply.tx_id_ = tx_data->txn_id_; // Assuming TxData has txn_id_
    
    // Clean up tx_data allocated by Frame::CreateTxnCommand
    delete tx_data;
    callback(reply);
  };
  
  // Log_info("Sending Dispatch to Sequencer");
  Future::safe_release(proxy->async_Dispatch(tx_data->txn_id_, md, fuattr));
}

} // namespace janus
