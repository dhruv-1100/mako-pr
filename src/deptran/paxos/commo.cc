
#include "commo.h"
#include "../rcc/graph.h"
#include "../rcc/graph_marshaler.h"
#include "../command.h"
#include "../procedure.h"
#include "../command_marshaler.h"
#include "../rcc_rpc.h"
#include <algorithm>

namespace janus {

MultiPaxosCommo::MultiPaxosCommo(rusty::Arc<PollThreadWorker> poll) : Communicator(poll) {
}

void MultiPaxosCommo::BroadcastPrepare(parid_t par_id,
                                       slotid_t slot_id,
                                       ballot_t ballot,
                                       const function<void(Future*)>& cb) {
  verify(0);
  // auto proxies = rpc_par_proxies_[par_id];
  // for (auto& p : proxies) {
  //   if (Config::GetConfig()->SiteById(p.first).role==2) continue; 
  //   auto proxy = (MultiPaxosProxy*) p.second;
  //   FutureAttr fuattr;
  //   fuattr.callback = cb;
  //   Future::safe_release(proxy->async_Prepare(slot_id, ballot, fuattr));
  // }
}

shared_ptr<PaxosPrepareQuorumEvent>
MultiPaxosCommo::BroadcastPrepare(parid_t par_id,
                                  slotid_t slot_id,
                                  ballot_t ballot) {
  verify(0);
  int n = std::max(1, Config::GetConfig()->GetPartitionSize(par_id)-1);
  auto e = Reactor::CreateSpEvent<PaxosPrepareQuorumEvent>(n, n); //marker:ansh debug
  // auto proxies = rpc_par_proxies_[par_id];
  // int cur_batch_idx = current_proxy_batch_idx;
  // current_proxy_batch_idx=(current_proxy_batch_idx+1)%proxy_batch_size;
  // for (int i=0;i<n+1;i++) {
  //   auto p = proxies.at(cur_batch_idx*(Config::GetConfig()->GetPartitionSize(par_id)) + i);
  //   if (Config::GetConfig()->SiteById(p.first).role==2) continue; 
  //   auto proxy = (MultiPaxosProxy*) p.second;
  //   FutureAttr fuattr;
  //   fuattr.callback = [e, ballot](Future* fu) {
  //     ballot_t b = 0;
  //     fu->get_reply() >> b;
  //     e->FeedResponse(b==ballot);
  //     // TODO add max accepted value.
  //   };
  //   Future::safe_release(proxy->async_Prepare(slot_id, ballot, fuattr));
  // }
  return e;
}

shared_ptr<PaxosAcceptQuorumEvent>
MultiPaxosCommo::BroadcastAccept(parid_t par_id,
                                 slotid_t slot_id,
                                 ballot_t ballot,
                                 shared_ptr<Marshallable> cmd) {
  int n = Config::GetConfig()->GetPartitionSize(par_id);
  int k = (n%2 == 0) ? n/2 : (n/2 + 1);
  auto e = Reactor::CreateSpEvent<PaxosAcceptQuorumEvent>(n, k);
  auto proxies = rpc_par_proxies_[par_id];
  vector<Future*> fus;
  int cur_batch_idx = current_proxy_batch_idx;
  current_proxy_batch_idx=(current_proxy_batch_idx+1)%proxy_batch_size;
  for (int i=0;i<n;i++) {
    auto p = proxies.at(cur_batch_idx*(Config::GetConfig()->GetPartitionSize(par_id)) + i);
    if (Config::GetConfig()->SiteById(p.first).role==2) continue; 
    auto proxy = (MultiPaxosProxy*) p.second;
    FutureAttr fuattr;
    fuattr.callback = [e, ballot] (Future* fu) {
      ballot_t b = 0;
      fu->get_reply() >> b;
      bool vote_yes = (b == ballot);
      Log_info("BroadcastAccept callback: expected_ballot=%d, received_ballot=%d, vote_yes=%d",
               ballot, b, vote_yes);
      e->FeedResponse(vote_yes);
    };
    MarshallDeputy md(cmd);
    auto f = proxy->async_Accept(slot_id, ballot, md, fuattr);
    Future::safe_release(f);
  }
  return e;
}

void MultiPaxosCommo::BroadcastAccept(parid_t par_id,
                                      slotid_t slot_id,
                                      ballot_t ballot,
                                      shared_ptr<Marshallable> cmd,
                                      const function<void(Future*)>& cb) {
  verify(0);
  // int n = Config::GetConfig()->GetPartitionSize(par_id)-1;
  // auto proxies = rpc_par_proxies_[par_id];
  // vector<Future*> fus;
  // int cur_batch_idx = current_proxy_batch_idx;
  // current_proxy_batch_idx=(current_proxy_batch_idx+1)%proxy_batch_size;
  // for (int i=0;i<n+1;i++) {
  //   auto p = proxies.at(cur_batch_idx*(Config::GetConfig()->GetPartitionSize(par_id)) + i);
  //   if (Config::GetConfig()->SiteById(p.first).role==2) continue; 
  //   auto proxy = (MultiPaxosProxy*) p.second;
  //   FutureAttr fuattr;
  //   fuattr.callback = cb;
  //   MarshallDeputy md(cmd);
  //   auto f = proxy->async_Accept(slot_id, ballot, md, fuattr);
  //   Future::safe_release(f);
  // }
}

/**
 * @brief forward the committed log the learner 
 * Within the same data center
 */
void MultiPaxosCommo::ForwardToLearner(parid_t par_id,
                                       uint64_t slot,
                                       ballot_t ballot,
                                       shared_ptr<Marshallable> cmd,
                                       const std::function<void(uint64_t, ballot_t)>& cb) {
  int n = std::max(1, Config::GetConfig()->GetPartitionSize(par_id)-1);
  auto proxies = rpc_par_proxies_[par_id];
  vector<Future*> fus;
  int cur_batch_idx = current_proxy_batch_idx;
  current_proxy_batch_idx=(current_proxy_batch_idx+1)%proxy_batch_size;

  //auto e = Reactor::CreateSpEvent<PaxosAcceptQuorumEvent>(1,1);

  for (int i=0;i<n+1;i++) {
    auto p = proxies.at(cur_batch_idx*(Config::GetConfig()->GetPartitionSize(par_id)) + i);
    if (Config::GetConfig()->SiteById(p.first).role!=2) continue; 
     auto proxy = (MultiPaxosProxy*) p.second;
     FutureAttr fuattr;
     fuattr.callback = [/*e, */cb] (Future* fu) {
        if (fu->get_error_code()!=0) {
          Log_info("received an error message6");
          return;
        }
        uint64_t slot;
        ballot_t ballot;
        // if the learner is killed at this moment, throw an error
        // in datacenter failover, keep learners are alive
        fu->get_reply() >> slot >> ballot;
        cb(slot, ballot);
        //e->FeedResponse(1);
      };
     MarshallDeputy md(cmd);
     auto f = proxy->async_ForwardToLearnerServer(par_id, slot, ballot, md, fuattr);
     Future::safe_release(f);

    // auto p = proxies.at(cur_batch_idx*(Config::GetConfig()->GetPartitionSize(par_id)) + i);
    // if (Config::GetConfig()->SiteById(p.first).role!=2) continue; 
    //  auto proxy = (MultiPaxosProxy*) p.second;
    //  MarshallDeputy md(cmd);
    //  uint64_t *slotr;
    //  ballot_t *ballotr;
    //  proxy->ForwardToLearnerServer(par_id, slot, ballot, md, slotr, ballotr);
    //  cb(*slotr, *ballotr);
  }
  //e->Wait();
}

void MultiPaxosCommo::BroadcastDecide(const parid_t par_id,
                                      const slotid_t slot_id,
                                      const ballot_t ballot,
                                      const shared_ptr<Marshallable> cmd) {
  Log_info("BroadcastDecide ENTRY: par_id=%d slot=%d", par_id, slot_id);
  fflush(stdout);
  Log_info("BroadcastDecide: about to GetPartitionSize");
  int n = Config::GetConfig()->GetPartitionSize(par_id);
  Log_info("BroadcastDecide: n=%d, about to get proxies from par_id=%d", n, par_id);
  fflush(stdout);
  verify(rpc_par_proxies_.count(par_id) > 0);
  auto proxies = rpc_par_proxies_[par_id];
  Log_info("BroadcastDecide: proxies.size()=%lu", proxies.size());
  vector<Future*> fus;
  // Use cur_batch_idx = 0 since we only have one batch of proxies
  // The batch mechanism is for round-robin RPC distribution across multiple proxy sets
  int cur_batch_idx = 0;
  Log_info("BroadcastDecide: par_id=%d slot=%d n=%d proxies=%lu cur_batch_idx=%d", par_id, slot_id, n, proxies.size(), cur_batch_idx);
  fflush(stdout);
  for (int i=0;i<n;i++) {
    int index = cur_batch_idx*(Config::GetConfig()->GetPartitionSize(par_id)) + i;
    Log_info("BroadcastDecide: loop i=%d, accessing proxies[%d], proxies.size()=%lu", i, index, proxies.size());
    fflush(stdout);
    if ((size_t)index >= proxies.size()) {
      Log_fatal("BroadcastDecide: index %d out of bounds (proxies.size()=%lu)", index, proxies.size());
      verify(0);
    }
    auto p = proxies.at(index);
    if (Config::GetConfig()->SiteById(p.first).role==2) {
      Log_info("BroadcastDecide: skipping site %d (role==2)", p.first);
      continue;
    }
    Log_info("BroadcastDecide: sending Decide to site %d", p.first);
    auto proxy = (MultiPaxosProxy*) p.second;
    FutureAttr fuattr;
    fuattr.callback = [](Future* fu) {};
    MarshallDeputy md(cmd);
    auto f = proxy->async_Decide(slot_id, ballot, md, fuattr);
    Future::safe_release(f);
  }
  Log_info("BroadcastDecide: loop complete, sent %d Decide RPCs", n);
}

shared_ptr<PaxosAcceptQuorumEvent>
MultiPaxosCommo::BroadcastBulkPrepare(parid_t par_id,
                                      shared_ptr<Marshallable> cmd,
                                      function<void(ballot_t, int)> cb) {
  verify(0);
  //Log_info("BroadcastBulkPrepare: i am here");
  int n = std::max(1, Config::GetConfig()->GetPartitionSize(par_id)-1);
  int k = std::max(1, (n%2 == 0) ? n/2 : (n/2 + 1));
  auto e = Reactor::CreateSpEvent<PaxosAcceptQuorumEvent>(n, k); // marker:debug
  //Log_info("BroadcastBulkPrepare: i am here partition size %d", n);
  // auto proxies = rpc_par_proxies_[par_id];
  // vector<Future*> fus;
  // int cur_batch_idx = current_proxy_batch_idx;
  // current_proxy_batch_idx=(current_proxy_batch_idx+1)%proxy_batch_size;
  // for (int i=0;i<n+1;i++) {
  //   auto p = proxies.at(cur_batch_idx*(Config::GetConfig()->GetPartitionSize(par_id)) + i);
  //   if (Config::GetConfig()->SiteById(p.first).role==2) continue; 
  //   if (Config::GetConfig()->SiteById(p.first).role==0) continue;
  //   auto proxy = (MultiPaxosProxy*) p.second;
  //   FutureAttr fuattr;
  //   fuattr.callback = [e, cb] (Future* fu) {
  //     i32 valid;
  //     i32 ballot;
  //     fu->get_reply() >> ballot >> valid;
  //     //Log_info("Received response %d %d", ballot, valid);
  //     cb(ballot, valid);
  //     e->FeedResponse(valid);
  //   };
  //   verify(cmd != nullptr);
  //   MarshallDeputy md(cmd);
  //   auto f = proxy->async_BulkPrepare(md, fuattr);
  //   Future::safe_release(f);
  // }
  return e;
}

shared_ptr<PaxosAcceptQuorumEvent>
MultiPaxosCommo::BroadcastPrepare2(parid_t par_id,
                                 shared_ptr<Marshallable> cmd,
                                 const std::function<void(MarshallDeputy, ballot_t, int)>& cb) {
  verify(0);
  int n = std::max(1, Config::GetConfig()->GetPartitionSize(par_id)-1);
  int k = std::max(1, (n%2 == 0) ? n/2 : (n/2 + 1));
  auto e = Reactor::CreateSpEvent<PaxosAcceptQuorumEvent>(n, k); //marker:debug
  // auto proxies = rpc_par_proxies_[par_id];
  // vector<Future*> fus;
  // //Log_info("paxos commo bulkaccept: length proxies %d", proxies.size());
  // int cur_batch_idx = current_proxy_batch_idx;
  // current_proxy_batch_idx=(current_proxy_batch_idx+1)%proxy_batch_size;
  // for (int i=0;i<n+1;i++) {
  //   auto p = proxies.at(cur_batch_idx*(Config::GetConfig()->GetPartitionSize(par_id)) + i);
  //   if (Config::GetConfig()->SiteById(p.first).role==2) continue; 
  //   auto proxy = (MultiPaxosProxy*) p.second;
  //   FutureAttr fuattr;
  //   fuattr.callback = [e, cb] (Future* fu) {
  //     i32 valid;
  //     i32 ballot;
  //     MarshallDeputy response_val;
  //     fu->get_reply() >> ballot >> valid >> response_val;
  //     //Log_info("BroadcastPrepare2: received response: %d %d", ballot, valid);
  //     cb(response_val, ballot, valid);
  //     e->FeedResponse(valid);
  //   };
  //   verify(cmd != nullptr);
  //   MarshallDeputy md(cmd);
  //   auto f = proxy->async_BulkPrepare2(md, fuattr);
  //   Future::safe_release(f);
  // }
  return e;
}

// Within the same data center
shared_ptr<PaxosAcceptQuorumEvent>
MultiPaxosCommo::BroadcastHeartBeat(parid_t par_id,
                                    shared_ptr<Marshallable> cmd,
                                    const function<void(ballot_t, int)>& cb) {
  int n = std::max(1, Config::GetConfig()->GetPartitionSize(par_id)-1);
  int k = std::max(1, (n%2 == 0) ? n/2 : (n/2 + 1));
  auto e = Reactor::CreateSpEvent<PaxosAcceptQuorumEvent>(n, k);
  auto proxies = rpc_par_proxies_[par_id];
  vector<Future*> fus;
  int cur_batch_idx = current_proxy_batch_idx;
  current_proxy_batch_idx=(current_proxy_batch_idx+1)%proxy_batch_size;
  for (int i=0;i<n+1;i++) {
    auto p = proxies.at(cur_batch_idx*(Config::GetConfig()->GetPartitionSize(par_id)) + i);
    if (Config::GetConfig()->SiteById(p.first).role==2) continue; 
    auto proxy = (MultiPaxosProxy*) p.second;
    FutureAttr fuattr;
    fuattr.callback = [e, cb] (Future* fu) {
      if (fu->get_error_code()!=0) {
        Log_info("received an error message5");
        return;
      }
      i32 valid;
      i32 ballot;
      fu->get_reply() >> ballot >> valid;
      cb(ballot, valid);
      e->FeedResponse(valid);
    };
    verify(cmd != nullptr);
    MarshallDeputy md(cmd);
    auto f = proxy->async_Heartbeat(md, fuattr);
    Future::safe_release(f);
  }
  return e;
}

// Distant data centers
shared_ptr<PaxosAcceptQuorumEvent>
MultiPaxosCommo::BroadcastSyncLog(parid_t par_id,
                                  shared_ptr<Marshallable> cmd,
                                  const std::function<void(shared_ptr<MarshallDeputy>, ballot_t, int)>& cb) {
  is_broadcast_syncLog = true;
  Log_info("invoke BroadcastSyncLog to prepare for the failover");
  int n = std::max(1, Config::GetConfig()->GetPartitionSize(par_id)-1);
  int k = std::max(1, (n%2 == 0) ? n/2 : (n/2 + 1));
  auto e = Reactor::CreateSpEvent<PaxosAcceptQuorumEvent>(n, k);
  auto proxies = rpc_par_proxies_[par_id];
  vector<Future*> fus;
  int cur_batch_idx = current_proxy_batch_idx;
  current_proxy_batch_idx=(current_proxy_batch_idx+1)%proxy_batch_size;
  for (int i=0;i<n+1;i++) {
    auto p = proxies.at(cur_batch_idx*(Config::GetConfig()->GetPartitionSize(par_id)) + i);
    if (Config::GetConfig()->SiteById(p.first).role==2) continue; 
    if (Config::GetConfig()->SiteById(p.first).role==0) continue;
    auto proxy = (MultiPaxosProxy*) p.second;
    FutureAttr fuattr;
    fuattr.callback = [e, cb] (Future* fu) {
      if (fu->get_error_code()!=0) {
        Log_info("received an error message3");
        return;
      }
      i32 valid;
      i32 ballot;
      MarshallDeputy response_val;
      fu->get_reply() >> ballot >> valid >> response_val;
      auto sp_md = make_shared<MarshallDeputy>(response_val);
      cb(sp_md, ballot, valid);
      e->FeedResponse(valid);
    };
    verify(cmd != nullptr);
    MarshallDeputy md(cmd);
    auto f = proxy->async_SyncLog(md, fuattr);
    Future::safe_release(f);
  }
  return e;
}

shared_ptr<PaxosAcceptQuorumEvent>
MultiPaxosCommo::BroadcastSyncNoOps(parid_t par_id,
                                  shared_ptr<Marshallable> cmd,
                                  const std::function<void(ballot_t, int)>& cb) {
  int n = std::max(1, Config::GetConfig()->GetPartitionSize(par_id)-1);
  int k = std::max(1, (n%2 == 0) ? n/2 : (n/2 + 1));
  // not old leader, not new leader(old learner)
  auto e = Reactor::CreateSpEvent<PaxosAcceptQuorumEvent>(n-1, n-1);
  auto proxies = rpc_par_proxies_[par_id];
  vector<Future*> fus;
  int cur_batch_idx = current_proxy_batch_idx;
  current_proxy_batch_idx=(current_proxy_batch_idx+1)%proxy_batch_size;
  for (int i=0;i<n+1;i++) {
    auto p = proxies.at(cur_batch_idx*(Config::GetConfig()->GetPartitionSize(par_id)) + i);
    if (Config::GetConfig()->SiteById(p.first).role==2) continue;
    if (Config::GetConfig()->SiteById(p.first).role==0) continue; // ??? why skip itself
    auto proxy = (MultiPaxosProxy*) p.second;
    FutureAttr fuattr;
    fuattr.callback = [e, cb] (Future* fu) {
      if (fu->get_error_code()!=0) {
        Log_info("received an error message4");
        return;
      }
      i32 valid;
      i32 ballot;
      fu->get_reply() >> ballot >> valid;
      cb(ballot, valid);
      e->FeedResponse(valid);
    };
    verify(cmd != nullptr);
    MarshallDeputy md(cmd);
    auto f = proxy->async_SyncNoOps(md, fuattr);
    Future::safe_release(f);
  }
  return e;
}

shared_ptr<PaxosAcceptQuorumEvent>
MultiPaxosCommo::BroadcastSyncCommit(parid_t par_id,
                                  shared_ptr<Marshallable> cmd,
                                  const std::function<void(ballot_t, int)>& cb) {
  int n = std::max(1, Config::GetConfig()->GetPartitionSize(par_id)-1);
  int k = std::max(1, (n%2 == 0) ? n/2 : (n/2 + 1));
  auto e = Reactor::CreateSpEvent<PaxosAcceptQuorumEvent>(1, 1);
  e->FeedResponse(1);
  // auto proxies = rpc_par_proxies_[par_id];
  // vector<Future*> fus;
  // int cur_batch_idx = current_proxy_batch_idx;
  // current_proxy_batch_idx=(current_proxy_batch_idx+1)%proxy_batch_size;
  // for (int i=0;i<n+1;i++) {
  //   auto p = proxies.at(cur_batch_idx*(Config::GetConfig()->GetPartitionSize(par_id)) + i);
  //   if (Config::GetConfig()->SiteById(p.first).role==2) continue;
  //   if (Config::GetConfig()->SiteById(p.first).role==0) continue;
  //   auto proxy = (MultiPaxosProxy*) p.second;
  //   FutureAttr fuattr;
  //   fuattr.callback = [e, cb] (Future* fu) {
  //     i32 valid;
  //     i32 ballot;
  //     fu->get_reply() >> ballot >> valid;
  //     cb(ballot, valid);
  //     e->FeedResponse(valid);
  //   };
  //   verify(cmd != nullptr);
  //   MarshallDeputy md(cmd);
  //   auto f = proxy->async_SyncCommit(md, fuattr);
  //   Future::safe_release(f);
  // }
  return e;
}

// Distant data center
shared_ptr<PaxosAcceptQuorumEvent>
MultiPaxosCommo::BroadcastBulkAccept(parid_t par_id,
                                 shared_ptr<Marshallable> cmd,
                                 const function<void(ballot_t, int)>& cb) {
  int n = std::max(1, Config::GetConfig()->GetPartitionSize(par_id)-1);
  int k = std::max(1, (n%2 == 0) ? n/2 : (n/2 + 1));
  auto e = Reactor::CreateSpEvent<PaxosAcceptQuorumEvent>(n, k); //marker:debug
  auto proxies = rpc_par_proxies_[par_id];
  vector<Future*> fus;
  int cur_batch_idx = current_proxy_batch_idx;
  current_proxy_batch_idx=(current_proxy_batch_idx+1)%proxy_batch_size;
  //Log_info("cur_batch_idx:%d",cur_batch_idx);
  for (int i=0;i<n+1;i++) {
    auto p = proxies.at(cur_batch_idx*(Config::GetConfig()->GetPartitionSize(par_id)) + i);
    if (Config::GetConfig()->SiteById(p.first).role==2) continue;
    auto proxy = (MultiPaxosProxy*) p.second;  // a Proxy pool for the concurrent request
    FutureAttr fuattr;
    int st = p.first;
    fuattr.callback = [e, cb, st] (Future* fu) {
      if (fu->get_error_code()!=0) {
        Log_info("received an error message2");
        return;
      }
      i32 valid;
      i32 ballot;
      fu->get_reply() >> ballot >> valid;
       // it's possible during failure because the client can receive reponse even the distant server shutdowns
      if (!valid)
        Log_debug("Accept invalid response received from %d site", st);
      cb(ballot, valid);
      e->FeedResponse(valid);
    };
    verify(cmd != nullptr);
    MarshallDeputy md(cmd);
    auto f = proxy->async_BulkAccept(md, fuattr);
    Future::safe_release(f);
  }
  return e;
}

// Distant data center
shared_ptr<PaxosAcceptQuorumEvent>
MultiPaxosCommo::BroadcastBulkDecide(parid_t par_id, 
                                     shared_ptr<Marshallable> cmd,
                                     const function<void(ballot_t, int)>& cb){
  auto proxies = rpc_par_proxies_[par_id];
  int n = std::max(1, Config::GetConfig()->GetPartitionSize(par_id)-1);
  int k = std::max(1, (n%2 == 0) ? n/2 : (n/2 + 1));
  auto e = Reactor::CreateSpEvent<PaxosAcceptQuorumEvent>(n, k); //marker:debug 
  vector<Future*> fus;
  int cur_batch_idx = current_proxy_batch_idx;
  current_proxy_batch_idx=(current_proxy_batch_idx+1)%proxy_batch_size;
  for (int i=0;i<n+1;i++) {
    auto p = proxies.at(cur_batch_idx*(Config::GetConfig()->GetPartitionSize(par_id)) + i);
    if (Config::GetConfig()->SiteById(p.first).role==2) continue;
    auto proxy = (MultiPaxosProxy*) p.second;
    FutureAttr fuattr;
    fuattr.callback = [e, cb] (Future* fu) {
      if (fu->get_error_code()!=0) {
        Log_info("received an error message");
        return;
      }
      i32 valid;
      i32 ballot;
      fu->get_reply() >> ballot >> valid;
      cb(ballot, valid);
      e->FeedResponse(valid);
    };
    MarshallDeputy md(cmd);
    auto f = proxy->async_BulkDecide(md, fuattr);
    Future::safe_release(f);
  }
  return e;
}

} // namespace janus
