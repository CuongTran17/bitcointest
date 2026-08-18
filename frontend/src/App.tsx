import { useEffect, useState } from "react";
import {
  createAddress,
  createUser,
  fundFromFaucet,
  getBalance,
  getTransactions,
  getUsers,
  mineBlocks,
  sendTransaction
} from "./api";
import { MineButton } from "./components/MineButton";
import { ReceivePanel } from "./components/ReceivePanel";
import { SendPanel } from "./components/SendPanel";
import { TransactionHistory } from "./components/TransactionHistory";
import { UserSwitcher } from "./components/UserSwitcher";
import { WalletDashboard } from "./components/WalletDashboard";
import type { Balance, Transaction, User } from "./types";

export default function App() {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedWallet, setSelectedWallet] = useState("alice");
  const [balance, setBalance] = useState<Balance | null>(null);
  const [address, setAddress] = useState("");
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [message, setMessage] = useState("");

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
    ensureDefaultUsers().then(() => refresh("alice")).catch((error: Error) => setMessage(error.message));
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
      <TransactionHistory transactions={transactions} />
    </main>
  );
}
