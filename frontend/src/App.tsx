import { useEffect, useRef, useState } from "react";
import {
  createAddress,
  createUser,
  fundFromFaucet,
  getBalance,
  getBlockDetail,
  getBlocks,
  getMempool,
  getTransactionDetail,
  getTransactions,
  getUsers,
  getUtxos,
  mineBlocks,
  sendTransaction,
} from "./api";
import { BlockExplorer } from "./components/BlockExplorer";
import { MempoolView } from "./components/MempoolView";
import { MineButton } from "./components/MineButton";
import { ReceivePanel } from "./components/ReceivePanel";
import { SendPanel } from "./components/SendPanel";
import { TransactionDetailPanel } from "./components/TransactionDetailPanel";
import { TransactionHistory } from "./components/TransactionHistory";
import { UserSwitcher } from "./components/UserSwitcher";
import { UtxoViewer } from "./components/UtxoViewer";
import { WalletDashboard } from "./components/WalletDashboard";
import type {
  Balance,
  BlockDetail,
  BlockList,
  MempoolSummary,
  Transaction,
  TransactionDetail,
  User,
  UtxoSummary,
} from "./types";

export default function App() {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedWallet, setSelectedWallet] = useState("alice");
  const [balance, setBalance] = useState<Balance | null>(null);
  const [address, setAddress] = useState("");
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [message, setMessage] = useState("");
  const [selectedTxid, setSelectedTxid] = useState<string | null>(null);
  const [transactionDetail, setTransactionDetail] = useState<TransactionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const detailRequestId = useRef(0);

  const [utxoSummary, setUtxoSummary] = useState<UtxoSummary | null>(null);
  const [utxoLoading, setUtxoLoading] = useState(false);
  const [utxoError, setUtxoError] = useState("");
  const utxoRequestId = useRef(0);

  const [mempoolSummary, setMempoolSummary] = useState<MempoolSummary | null>(null);
  const [mempoolLoading, setMempoolLoading] = useState(false);
  const [mempoolError, setMempoolError] = useState("");
  const mempoolRequestId = useRef(0);

  const [blockList, setBlockList] = useState<BlockList | null>(null);
  const [selectedBlock, setSelectedBlock] = useState<BlockDetail | null>(null);
  const [blockLimit, setBlockLimit] = useState(20);
  const [blockLoading, setBlockLoading] = useState(false);
  const [blockDetailLoading, setBlockDetailLoading] = useState(false);
  const [blockError, setBlockError] = useState("");
  const [blockDetailError, setBlockDetailError] = useState("");
  const blockListRequestId = useRef(0);
  const blockDetailRequestId = useRef(0);

  async function handleSelectTransaction(txid: string) {
    const requestId = ++detailRequestId.current;
    setSelectedTxid(txid);
    setTransactionDetail(null);
    setDetailLoading(true);
    try {
      const detail = await getTransactionDetail(txid);
      if (requestId === detailRequestId.current) {
        setTransactionDetail(detail);
      }
    } catch (error) {
      if (requestId === detailRequestId.current) {
        setMessage(error instanceof Error ? error.message : "Failed to load transaction detail");
      }
    } finally {
      if (requestId === detailRequestId.current) {
        setDetailLoading(false);
      }
    }
  }

  async function refresh(walletName = selectedWallet) {
    setUsers(await getUsers());
    setBalance(await getBalance(walletName));
    setTransactions(await getTransactions(walletName));
  }

  async function refreshUtxos(walletName = selectedWallet) {
    const requestId = ++utxoRequestId.current;
    setUtxoLoading(true);
    setUtxoError("");
    try {
      const summary = await getUtxos(walletName);
      if (requestId === utxoRequestId.current) {
        setUtxoSummary(summary);
      }
    } catch (error) {
      if (requestId === utxoRequestId.current) {
        setUtxoError((error as Error).message);
      }
    } finally {
      if (requestId === utxoRequestId.current) {
        setUtxoLoading(false);
      }
    }
  }

  async function refreshMempool() {
    const requestId = ++mempoolRequestId.current;
    setMempoolLoading(true);
    setMempoolError("");
    try {
      const summary = await getMempool();
      if (requestId === mempoolRequestId.current) {
        setMempoolSummary(summary);
      }
    } catch (error) {
      if (requestId === mempoolRequestId.current) {
        setMempoolError((error as Error).message);
      }
    } finally {
      if (requestId === mempoolRequestId.current) {
        setMempoolLoading(false);
      }
    }
  }

  async function selectBlock(blockRef: string) {
    const requestId = ++blockDetailRequestId.current;
    setBlockDetailLoading(true);
    setBlockDetailError("");
    try {
      const detail = await getBlockDetail(blockRef);
      if (requestId === blockDetailRequestId.current) {
        setSelectedBlock(detail);
      }
    } catch (error) {
      if (requestId === blockDetailRequestId.current) {
        setBlockDetailError((error as Error).message);
      }
    } finally {
      if (requestId === blockDetailRequestId.current) {
        setBlockDetailLoading(false);
      }
    }
  }

  async function refreshBlocks(limit = blockLimit, selectTip = false) {
    const requestId = ++blockListRequestId.current;
    setBlockLoading(true);
    setBlockError("");
    try {
      const result = await getBlocks(limit);
      if (requestId !== blockListRequestId.current) return;
      setBlockList(result);
      if ((selectTip || selectedBlock === null) && result.blocks.length > 0) {
        await selectBlock(String(result.blocks[0].height));
      } else if (result.blocks.length === 0) {
        setSelectedBlock(null);
      }
    } catch (error) {
      if (requestId === blockListRequestId.current) {
        setBlockError((error as Error).message);
      }
    } finally {
      if (requestId === blockListRequestId.current) {
        setBlockLoading(false);
      }
    }
  }

  async function refreshGlobalData(selectTip = false) {
    await Promise.allSettled([
      refreshMempool(),
      refreshBlocks(blockLimit, selectTip),
    ]);
  }

  async function refreshWalletData(walletName = selectedWallet) {
    await Promise.allSettled([
      refresh(walletName),
      refreshUtxos(walletName),
    ]);
  }

  async function ensureDefaultUsers() {
    const currentUsers = await getUsers();
    if (currentUsers.length === 0) {
      await createUser("Alice", "alice");
      await createUser("Bob", "bob");
      await createUser("Miner", "miner");
    }
  }

  useEffect(() => {
    ensureDefaultUsers()
      .then(async () => {
        await refreshWalletData("alice");
      })
      .catch((error: Error) => setMessage(error.message));
  }, []);

  useEffect(() => {
    refreshMempool().catch(() => undefined);
    refreshBlocks(blockLimit, true).catch(() => undefined);
  }, []);

  async function handleAddress() {
    const result = await createAddress(selectedWallet);
    setAddress(result.address);
  }

  async function handleSend(toAddress: string, amountBtc: string) {
    await sendTransaction(selectedWallet, toAddress, amountBtc);
    setMessage("Transaction sent. Mine a block to confirm it.");
    await refreshWalletData();
    await refreshGlobalData();
  }

  async function handleFaucet() {
    await fundFromFaucet(selectedWallet, "10.00000000");
    setMessage(`${selectedWallet} funded from miner faucet.`);
    await refreshWalletData();
    await refreshGlobalData();
  }

  async function handleMine() {
    await mineBlocks("miner", 1);
    setMessage("Block mined successfully.");
    await refreshWalletData();
    await refreshGlobalData(true);
    if (selectedTxid) {
      handleSelectTransaction(selectedTxid).catch(() => {});
    }
  }

  return (
    <main className="app">
      <header className="app-header">
        <div className="brand-block">
          <h1>Local Bitcoin Bank</h1>
          <p className="subtitle">Bitcoin Core Regtest Sandbox &amp; Explorer</p>
        </div>
        <div className="primary-actions">
          <button type="button" onClick={handleFaucet}>
            Faucet 10 BTC
          </button>
          <MineButton onMine={handleMine} />
        </div>
      </header>

      <UserSwitcher
        users={users}
        selectedWallet={selectedWallet}
        onSelect={(wallet) => {
          detailRequestId.current += 1;
          setSelectedTxid(null);
          setTransactionDetail(null);
          setDetailLoading(false);
          setSelectedWallet(wallet);
          refreshWalletData(wallet).catch(() => undefined);
        }}
      />

      <WalletDashboard walletName={selectedWallet} balance={balance} />

      <div className="grid">
        <ReceivePanel address={address} onCreateAddress={handleAddress} />
        <SendPanel onSend={handleSend} />
      </div>

      {message && <p className="message">{message}</p>}

      <TransactionHistory
        transactions={transactions}
        selectedTxid={selectedTxid}
        onSelectTransaction={handleSelectTransaction}
      />

      <TransactionDetailPanel detail={transactionDetail} loading={detailLoading} />

      <UtxoViewer
        walletName={selectedWallet}
        summary={utxoSummary}
        loading={utxoLoading}
        error={utxoError}
        onRefresh={() => refreshUtxos().catch(() => undefined)}
      />

      <MempoolView
        summary={mempoolSummary}
        loading={mempoolLoading}
        error={mempoolError}
        onRefresh={() => refreshMempool().catch(() => undefined)}
      />

      <BlockExplorer
        blockList={blockList}
        selectedBlock={selectedBlock}
        limit={blockLimit}
        loading={blockLoading}
        detailLoading={blockDetailLoading}
        error={blockError}
        detailError={blockDetailError}
        onLimitChange={(nextLimit) => {
          setBlockLimit(nextLimit);
          refreshBlocks(nextLimit, false).catch(() => undefined);
        }}
        onRefresh={() => refreshBlocks(blockLimit, false).catch(() => undefined)}
        onSelectBlock={(blockRef) => selectBlock(blockRef).catch(() => undefined)}
      />
    </main>
  );
}
