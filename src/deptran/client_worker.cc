#include <cmath>
#include "client_worker.h"
#include "frame.h"
#include "procedure.h"
#include "coordinator.h"
#include "workload.h"
#include "benchmark_control_rpc.h"

namespace janus {

ClientWorker::~ClientWorker() {
  if (tx_generator_) {
    delete tx_generator_;
  }
  for (auto c : created_coordinators_) {
    delete c;
  }
//  dispatch_pool_->release();

  // Shutdown PollThreadWorker if we own it
  if (poll_thread_worker_) {
    poll_thread_worker_->shutdown();
  }
}

void ClientWorker::ForwardRequestDone(Coordinator* coo,
                                      TxReply* output,
                                      DeferredReply* defer,
                                      TxReply& txn_reply) {
  verify(coo != nullptr);
  verify(output != nullptr);

  *output = txn_reply;

  bool have_more_time = timer_->elapsed() < duration;
  if (have_more_time && config_->client_type_ == Config::Open) {
    std::lock_guard<std::mutex> lock(coordinator_mutex);
    coo->forward_status_ = NONE;
    free_coordinators_.push_back(coo);
  } else if (!have_more_time) {
    Log_debug("times up. stop.");
    Log_debug("n_concurrent_ = %d", n_concurrent_);
//    finish_mutex.lock();
    n_concurrent_--;
    if (n_concurrent_ == 0) {
      Log_debug("all coordinators finished... signal done");
//      finish_cond.signal();
    } else {
      Log_debug("waiting for %d more coordinators to finish", n_concurrent_);
    }
//    finish_mutex.unlock();
  }

  defer->reply();
}

void ClientWorker::RequestDone(Coordinator* coo, TxReply& txn_reply) {
  verify(coo != nullptr);
  Log_info("ClientWorker::RequestDone received callback from tx_id %" PRIx64 ", res=%d", txn_reply.tx_id_, txn_reply.res_);

  if (txn_reply.res_ == SUCCESS) {
    success++;
    if (ccsi) {
      struct timespec t;
      clock_gettime(&t);
      int32_t type = 10; // Default to TPCC_NEW_ORDER
      if (coo->cmd_ && coo->cmd_->type_ != 0) {
          type = coo->cmd_->type_;
      }
      ccsi->txn_success_one(id, type, t, 0.0, 0.0, txn_reply.n_try_);
    } else {
      Log_warn("ClientWorker::RequestDone: ccsi is NULL, cannot report success");
    }
  }
  Log_info("ClientWorker::RequestDone: res=%d", txn_reply.res_);
  num_txn++;
  num_try.fetch_add(txn_reply.n_try_);

  bool have_more_time = timer_->elapsed() < duration;
  Log_info("received callback from tx_id %" PRIx64, txn_reply.tx_id_);
  Log_info("elapsed: %2.2f; duration: %d", timer_->elapsed(), duration);
  if (have_more_time && config_->client_type_ == Config::Open) {
    std::lock_guard<std::mutex> lock(coordinator_mutex);
    free_coordinators_.push_back(coo);
  } else if (have_more_time && config_->client_type_ == Config::Closed) {
    if (txn_reply.res_ == SUCCESS) {
      Log_info("ClientWorker::RequestDone: Tx %" PRIx64 " succeeded. Calling DispatchRequest.", txn_reply.tx_id_);
    } else {
      Log_warn("ClientWorker::RequestDone: Tx %" PRIx64 " failed with res=%d. Calling DispatchRequest.", txn_reply.tx_id_, txn_reply.res_);
    }
    DispatchRequest(coo);
  } else if (!have_more_time) {
    Log_debug("times up. stop.");
    Log_debug("n_concurrent_ = %d", n_concurrent_);
//    finish_mutex.lock();
    n_concurrent_--;
    verify(n_concurrent_ >= 0);
    if (n_concurrent_ == 0) {
      Log_debug("all coordinators finished... signal done");
//      finish_cond.signal();
    } else {
      Log_debug("waiting for %d more coordinators to finish", n_concurrent_);
      Log_debug("transactions they are processing:");
      // for debug purpose, print ongoing transaction ids.
      for (auto c : created_coordinators_) {
        if (c->ongoing_tx_id_ > 0) {
          Log_debug("\t %" PRIx64, c->ongoing_tx_id_);
        }
      }
    }
//    finish_mutex.unlock();
  } else {
    verify(0);
  }
}

Coordinator* ClientWorker::FindOrCreateCoordinator() {
  std::lock_guard<std::mutex> lock(coordinator_mutex);

  Coordinator* coo = nullptr;

  if (free_coordinators_.size() > 0) {
    coo = dynamic_cast<Coordinator*>(free_coordinators_.back());
    free_coordinators_.pop_back();
  } else {
    if (created_coordinators_.size() == UINT16_MAX) {
      return nullptr;
    }
    verify(created_coordinators_.size() <= UINT16_MAX);
    coo = CreateCoordinator(created_coordinators_.size());
  }

  return coo;
}

Coordinator* ClientWorker::CreateCoordinator(uint16_t offset_id) {

  cooid_t coo_id = cli_id_;
  coo_id = (coo_id << 16) + offset_id;
  auto coo = frame_->CreateCoordinator(coo_id,
                                       config_,
                                       benchmark,
                                       ccsi,
                                       id,
                                       txn_reg_);
  coo->loc_id_ = my_site_.locale_id;
  coo->commo_ = commo_;
  coo->frame_ = frame_;
  coo->forward_status_ = forward_requests_to_leader_ ? FORWARD_TO_LEADER : NONE;
  Log_debug("coordinator %d created at site %d: forward %d",
            coo->coo_id_,
            this->my_site_.id,
            coo->forward_status_);
  created_coordinators_.push_back(coo);
  return coo;
}

void ClientWorker::Work() {
  Log_info("%s: %d", __FUNCTION__, this->cli_id_);
  txn_reg_ = std::make_shared<TxnRegistry>();
  verify(config_ != nullptr);
  Workload* workload = Workload::CreateWorkload(config_);
  workload->txn_reg_ = txn_reg_;
  workload->RegisterPrecedures();

  commo_->WaitConnectClientLeaders();
  if (ccsi) {
    Log_info("waiting for start signal");
    ccsi->wait_for_start(id);
    Log_info("received start signal");
  }
  Log_info("after wait for start");

  timer_ = new Timer();
  timer_->start();

  if (config_->client_type_ == Config::Closed) {
    Log_info("closed loop clients.");
    verify(n_concurrent_ > 0);
    int n = n_concurrent_;
    auto sp_job = std::make_shared<OneTimeJob>([this] () {
      for (uint32_t n_tx = 0; n_tx < n_concurrent_; n_tx++) {
        auto coo = CreateCoordinator(n_tx);
        Log_info("create coordinator %d", coo->coo_id_);
        Log_info("ClientWorker::Work: Dispatching request for coordinator %d", coo->coo_id_);
        this->DispatchRequest(coo);
      }
    });
    poll_thread_worker_->add(dynamic_pointer_cast<Job>(sp_job));
  } else {
    Log_info("open loop clients.");
    const std::chrono::nanoseconds wait_time
        ((int) (pow(10, 9) * 1.0 / (double) config_->client_rate_));
    double tps = 0;
    long txn_count = 0;
    auto start = std::chrono::steady_clock::now();
    std::chrono::nanoseconds elapsed;

    while (timer_->elapsed() < duration) {
      while (tps < config_->client_rate_ && timer_->elapsed() < duration) {
        auto coo = FindOrCreateCoordinator();
        if (coo != nullptr) {
          auto p_job = (Job*)new OneTimeJob([this, coo] () {
            this->DispatchRequest(coo);
          });
          shared_ptr<Job> sp_job(p_job);
          poll_thread_worker_->add(sp_job);
          txn_count++;
          elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>
              (std::chrono::steady_clock::now() - start);
          tps = (double) txn_count / elapsed.count() * pow(10, 9);
        }
      }
      auto next_time = std::chrono::steady_clock::now() + wait_time;
      std::this_thread::sleep_until(next_time);
      elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>
          (std::chrono::steady_clock::now() - start);
      tps = (double) txn_count / elapsed.count() * pow(10, 9);
    }
    Log_debug("exit client dispatch loop...");
  }

//  finish_mutex.lock();
  while (n_concurrent_ > 0) {
    Log_debug("wait for finish... %d", n_concurrent_);
    sleep(1);
//    finish_cond.wait(finish_mutex);
  }
//  finish_mutex.unlock();

  Log_info("Finish:\nTotal: %u, Commit: %u, Attempts: %u, Running for %u\n",
           num_txn.load(),
           success.load(),
           num_try.load(),
           Config::GetConfig()->get_duration());
  fflush(stderr);
  fflush(stdout);
  if (ccsi) {
    Log_info("%s: wait_for_shutdown at client %d", __FUNCTION__, cli_id_);
    ccsi->wait_for_shutdown();
  }
  delete timer_;
  return;
}

void ClientWorker::AcceptForwardedRequest(TxRequest& request,
                                          TxReply* txn_reply,
                                          rrr::DeferredReply* defer) {
  const char* f = __FUNCTION__;

  // obtain free a coordinator first
  Coordinator* coo = nullptr;
  while (coo == nullptr) {
    coo = FindOrCreateCoordinator();
  }
  coo->forward_status_ = PROCESS_FORWARD_REQUEST;

  // run the task
  std::function<void()> task = [=]() {
    TxRequest req(request);
    req.callback_ = std::bind(&ClientWorker::ForwardRequestDone,
                              this,
                              coo,
                              txn_reply,
                              defer,
                              std::placeholders::_1);
    Log_debug("%s: running forwarded request at site %d", f, my_site_.id);
    coo->DoTxAsync(req);
  };
  task();
//  dispatch_pool_->run_async(task); // this causes bug
}

void ClientWorker::DispatchRequest(Coordinator* coo) {
  const char* f = __FUNCTION__;
  Log_info("ClientWorker::DispatchRequest start for cli_id %d", cli_id_);
  Log_debug("%s: %d", f, cli_id_);
  TxRequest req;
  {
    std::lock_guard<std::mutex> lock(this->request_gen_mutex);
    tx_generator_->GetTxRequest(&req, coo->coo_id_);
  }
  
  if (ccsi) {
      int32_t type = req.tx_type_;
      if (type == 0) type = 10;
      ccsi->txn_start_one(id, type);
  }
  struct timespec start_time;
  clock_gettime(&start_time);

  req.callback_ = [this, coo, start_time](TxReply& reply) {
    if (ccsi) {
        struct timespec end_time;
        clock_gettime(&end_time);
        double latency = timespec2ms(end_time) - timespec2ms(start_time);
        int32_t type = reply.txn_type_;
        if (type == 0) type = 10;
        if (reply.res_ == SUCCESS) {
            ccsi->txn_success_one(id, type, start_time, latency, 0, reply.n_try_);
        } else {
            ccsi->txn_reject_one(id, type, start_time, latency, 0, reply.n_try_);
        }
    }
    RequestDone(coo, reply);
  };

  coo->DoTxAsync(req);
  Log_info("ClientWorker::DispatchRequest end for cli_id %d", cli_id_);
}

ClientWorker::ClientWorker(
    uint32_t id,
    Config::SiteInfo& site_info,
    Config* config,
    ClientControlServiceImpl* ccsi,
    rusty::Arc<PollThreadWorker> poll_thread_worker) :
    id(id),
    my_site_(site_info),
    config_(config),
    cli_id_(site_info.id),
    benchmark(config->benchmark()),
    mode(config->get_mode()),
    duration(config->get_duration()),
    ccsi(ccsi),
    n_concurrent_(config->get_concurrent_txn()) {
  poll_thread_worker_ = !poll_thread_worker ? PollThreadWorker::create() : poll_thread_worker;
  frame_ = Frame::GetFrame(config->tx_proto_);
  tx_generator_ = frame_->CreateTxGenerator();
  txn_reg_ = std::make_shared<TxnRegistry>();
  tx_generator_->txn_reg_ = txn_reg_;
  tx_generator_->RegisterPrecedures();
  config->get_all_site_addr(servers_);
  num_txn.store(0);
  success.store(0);
  num_try.store(0);
  commo_ = frame_->CreateCommo(poll_thread_worker_);
  commo_->loc_id_ = my_site_.locale_id;
  forward_requests_to_leader_ =
      (config->replica_proto_ == MODE_MULTI_PAXOS && site_info.locale_id != 0) ? true
                                                                         : false;
  Log_debug("client %d created; forward %d",
            cli_id_,
            forward_requests_to_leader_);
}

} // namespace janus

