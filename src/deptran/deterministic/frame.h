#pragma once

#include "../constants.h"
#include "../frame.h"

namespace janus {

class DeterministicFrame : public Frame {
public:
  DeterministicFrame(int mode);
  Executor *CreateExecutor(cmdid_t cmd_id, TxLogServer *sched) override;
  Coordinator *CreateCoordinator(cooid_t coo_id, Config *config, int benchmark,
                                 ClientControlServiceImpl *ccsi, uint32_t id,
                                 shared_ptr<TxnRegistry> txn_reg) override;
  TxLogServer *CreateScheduler() override;
  vector<rrr::Service *>
  CreateRpcServices(uint32_t site_id, TxLogServer *dtxn_sched,
                    rusty::Arc<rrr::PollThreadWorker> poll_thread_worker,
                    ServerControlServiceImpl *scsi) override;
};

} // namespace janus
