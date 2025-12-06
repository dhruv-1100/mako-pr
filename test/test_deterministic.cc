#include "deptran/constants.h"
#include "deptran/deterministic/scheduler.h"
#include "deptran/procedure.h"
#include <gtest/gtest.h>

using namespace janus;

// Mock or subclass to access protected members if necessary
class TestSchedulerDeterministic : public SchedulerDeterministic {
public:
  TestSchedulerDeterministic() : SchedulerDeterministic() {
      // Overwrite app_next_ to avoid calling the real ExecuteNext
      app_next_ = [this](int slot, shared_ptr<Marshallable> cmd) -> int {
          std::lock_guard<std::recursive_mutex> lock(mtx_pending_);
          pending_txns_[slot] = cmd;
          MockExecuteNext();
          return 0;
      };
  }

  // Expose protected members for testing
  int32_t GetNextSlot() const { return next_slot_to_execute_; }
  void SetNextSlot(int32_t slot) { next_slot_to_execute_ = slot; }
  size_t GetPendingSize() const { return pending_txns_.size(); }

  void MockExecuteNext() {
      std::lock_guard<std::recursive_mutex> lock(mtx_pending_);
      while (pending_txns_.count(next_slot_to_execute_)) {
          // Simulate execution
          pending_txns_.erase(next_slot_to_execute_);
          next_slot_to_execute_++;
      }
  }
};

class DeterministicSchedulerTest : public ::testing::Test {
protected:
  TestSchedulerDeterministic *scheduler;

  void SetUp() override {
    // Initialize Config to avoid crash in TxLogServer constructor
    const char* argv[] = {"test_deterministic", "-f", "../config/deterministic_single.yml"};
    int argc = 3;
    Config::CreateConfig(argc, (char**)argv);
    scheduler = new TestSchedulerDeterministic(); 
  }

  void TearDown() override { delete scheduler; }
  
  shared_ptr<VecPieceData> CreateTx(txnid_t txn_id, int slot) {
      auto vpd = make_shared<VecPieceData>();
      vpd->sp_vec_piece_data_ = make_shared<vector<shared_ptr<TxPieceData>>>();
      auto piece = make_shared<TxPieceData>();
      piece->root_id_ = txn_id;
      piece->timestamp_ = slot; // Slot is stored in timestamp_
      vpd->sp_vec_piece_data_->push_back(piece);
      return vpd;
  }
};

TEST_F(DeterministicSchedulerTest, InitialState) {
  EXPECT_EQ(scheduler->GetNextSlot(), 1); // Initial slot is 1
  EXPECT_EQ(scheduler->GetPendingSize(), 0);
}

TEST_F(DeterministicSchedulerTest, SequentialExecution) {
  // Simulate receiving transactions in order
  auto tx1 = CreateTx(100, 1);
  auto tx2 = CreateTx(101, 2);

  // Add slot 1
  shared_ptr<Marshallable> cmd1 = tx1;
  scheduler->OnCommit(1, 0, cmd1); 

  EXPECT_EQ(scheduler->GetNextSlot(), 2);
  EXPECT_EQ(scheduler->GetPendingSize(), 0);
  
  // Add slot 2
  shared_ptr<Marshallable> cmd2 = tx2;
  scheduler->OnCommit(2, 0, cmd2);
  
  EXPECT_EQ(scheduler->GetNextSlot(), 3);
  EXPECT_EQ(scheduler->GetPendingSize(), 0);
}

TEST_F(DeterministicSchedulerTest, OutOfOrderExecution) {
  // Simulate receiving slot 3, then 1, then 2
  auto tx1 = CreateTx(100, 1);
  auto tx2 = CreateTx(101, 2);
  auto tx3 = CreateTx(102, 3);

  // Receive slot 3
  shared_ptr<Marshallable> cmd3 = tx3;
  scheduler->OnCommit(3, 0, cmd3);
  EXPECT_EQ(scheduler->GetNextSlot(), 1); // Should wait for 1
  EXPECT_EQ(scheduler->GetPendingSize(), 0); // PaxosServer buffers it, not Scheduler

  // Receive slot 1
  shared_ptr<Marshallable> cmd1 = tx1;
  scheduler->OnCommit(1, 0, cmd1);
  // Should execute 1, still wait for 2
  EXPECT_EQ(scheduler->GetNextSlot(), 2);
  EXPECT_EQ(scheduler->GetPendingSize(), 0); // Slot 3 still buffered in PaxosServer
  
  // Receive slot 2
  shared_ptr<Marshallable> cmd2 = tx2;
  scheduler->OnCommit(2, 0, cmd2);
  // Should execute 2 and 3
  EXPECT_EQ(scheduler->GetNextSlot(), 4);
  EXPECT_EQ(scheduler->GetPendingSize(), 0);
}

TEST_F(DeterministicSchedulerTest, DuplicateSlots) {
  auto tx1 = CreateTx(100, 1);
  shared_ptr<Marshallable> cmd1 = tx1;

  // First commit
  scheduler->OnCommit(1, 0, cmd1);
  EXPECT_EQ(scheduler->GetNextSlot(), 2);

  // Duplicate commit - should be ignored and not crash
  scheduler->OnCommit(1, 0, cmd1);
  EXPECT_EQ(scheduler->GetNextSlot(), 2);
}

TEST_F(DeterministicSchedulerTest, GapExecution) {
  // Slots: 1, 3, 5
  auto tx1 = CreateTx(100, 1);
  auto tx3 = CreateTx(102, 3);
  auto tx5 = CreateTx(104, 5);
  
  auto tx2 = CreateTx(101, 2);
  auto tx4 = CreateTx(103, 4);

  shared_ptr<Marshallable> cmd1 = tx1;
  shared_ptr<Marshallable> cmd3 = tx3;
  shared_ptr<Marshallable> cmd5 = tx5;
  shared_ptr<Marshallable> cmd2 = tx2;
  shared_ptr<Marshallable> cmd4 = tx4;

  // 1 arrives
  scheduler->OnCommit(1, 0, cmd1);
  EXPECT_EQ(scheduler->GetNextSlot(), 2);

  // 3 arrives (gap 2)
  scheduler->OnCommit(3, 0, cmd3);
  EXPECT_EQ(scheduler->GetNextSlot(), 2);

  // 5 arrives (gap 4)
  scheduler->OnCommit(5, 0, cmd5);
  EXPECT_EQ(scheduler->GetNextSlot(), 2);

  // 2 arrives -> executes 2, 3. Stops at 4.
  scheduler->OnCommit(2, 0, cmd2);
  EXPECT_EQ(scheduler->GetNextSlot(), 4);

  // 4 arrives -> executes 4, 5.
  scheduler->OnCommit(4, 0, cmd4);
  EXPECT_EQ(scheduler->GetNextSlot(), 6);
}
