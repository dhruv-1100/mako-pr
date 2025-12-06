#include "frame.h"
#include "../__dep__.h"
#include "../constants.h"
#include "coordinator.h"
#include "scheduler.h"
#include "../service.h"

#include "../paxos/commo.h"

namespace janus {

REG_FRAME(MODE_DETERMINISTIC, vector<string>({"deterministic"}),
          DeterministicFrame);

DeterministicFrame::DeterministicFrame(int mode) : Frame(mode) {}

Executor *DeterministicFrame::CreateExecutor(cmdid_t cmd_id,
                                             TxLogServer *sched) {
  // For now, we can reuse the default executor or create a specific one if
  // needed. Returning nullptr for now as the scheduler might handle execution
  // directly or we reuse existing ones. Ideally, we should have a
  // DeterministicExecutor if the execution logic is different. But based on the
  // plan, the scheduler will handle the deterministic order.
  return nullptr;
}

Coordinator *DeterministicFrame::CreateCoordinator(
    cooid_t coo_id, Config *config, int benchmark,
    ClientControlServiceImpl *ccsi, uint32_t id,
    shared_ptr<TxnRegistry> txn_reg) {
  auto coo = new CoordinatorDeterministic(coo_id, benchmark, ccsi, id);
  coo->txn_reg_ = txn_reg;
  return coo;
}

TxLogServer *DeterministicFrame::CreateScheduler() {
  auto sched = new SchedulerDeterministic();
  sched->frame_ = this;
  return sched;
}

vector<rrr::Service *> DeterministicFrame::CreateRpcServices(
    uint32_t site_id, TxLogServer *dtxn_sched,
    rusty::Arc<rrr::PollThreadWorker> poll_thread_worker,
    ServerControlServiceImpl *scsi) {
  return vector<rrr::Service *>({new ClassicServiceImpl(dtxn_sched, poll_thread_worker, scsi)});
}

Communicator *DeterministicFrame::CreateCommo(rusty::Arc<rrr::PollThreadWorker> poll_thread_worker) {
  return new MultiPaxosCommo(poll_thread_worker);
}

} // namespace janus
