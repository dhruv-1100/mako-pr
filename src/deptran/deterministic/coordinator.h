#pragma once

#include "../coordinator.h"

namespace janus {

class CoordinatorDeterministic : public Coordinator {
public:
  CoordinatorDeterministic(uint32_t coo_id, int32_t benchmark,
                           ClientControlServiceImpl *ccsi, uint32_t thread_id);

  void DoTxAsync(TxRequest &req) override;
  void Restart() override { verify(0); }
};

} // namespace janus
