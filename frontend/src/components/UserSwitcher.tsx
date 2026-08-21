import type { User } from "../types";

type Props = {
  users: User[];
  selectedWallet: string;
  onSelect: (walletName: string) => void;
};

export function UserSwitcher({ users, selectedWallet, onSelect }: Props) {
  return (
    <div className="wallet-switcher-container">
      <span className="label">Active Wallet:</span>
      <div className="segmented-control" role="tablist" aria-label="Wallet selector">
        {users.map((user) => (
          <button
            key={user.id}
            type="button"
            role="tab"
            aria-selected={user.wallet_name === selectedWallet}
            className={user.wallet_name === selectedWallet ? "active" : ""}
            onClick={() => onSelect(user.wallet_name)}
          >
            {user.name}
          </button>
        ))}
      </div>
    </div>
  );
}
