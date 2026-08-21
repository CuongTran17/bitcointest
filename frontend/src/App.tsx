import { useEffect, useRef, useState } from "react";
import {
  createAddress,
  createUser,
  fundFromFaucet,
  getBalance,
  getTransactionDetail,
  getTransactions,
  getUsers,
  mineBlocks,
  sendTransaction,
} from "./api";
import { MineButton } from "./components/MineButton";
import { ReceivePanel } from "./components/ReceivePanel";
import { SendPanel } from "./components/SendPanel";
import { TransactionDetailPanel } from "./components/TransactionDetailPanel";
import { TransactionHistory } from "./components/TransactionHistory";
import { UserSwitcher } from "./components/UserSwitcher";
import { WalletDashboard } from "./components/WalletDashboard";
import type { Balance, Transaction, TransactionDetail, User } from "./types";

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
      .then(() => refresh("alice"))
      .catch((error: Error) => setMessage(error.message));
  }, []);

  async function handleAddress() {
    const result = await createAddress(selectedWallet);
    setAddress(result.address);
  }

  async function handleSend(toAddress: string, amountBtc: string) {
    await sendTransaction(selectedWallet, toAddress, amountBtc);
    setMessage("Transaction sent. Mine a block to confirm it.");
    await refresh();
  }

  async function handleFaucet() {
    await fundFromFaucet(selectedWallet, "10.00000000");
    setMessage(`${selectedWallet} funded from miner faucet.`);
    await refresh();
  }

  async function handleMine() {
    await mineBlocks("miner", 1);
    setMessage("Block mined.");
    await refresh();
    if (selectedTxid) {
      handleSelectTransaction(selectedTxid).catch(() => {});
    }
  }

  return (
    <main className="app">
      <header>
        <h1>Local Bitcoin Bank</h1>
        <div className="actions">
          <button onClick={handleFaucet}>Faucet 10 BTC</button>
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
          refresh(wallet).catch((error: Error) => setMessage(error.message));
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
    </main>
  );
}
