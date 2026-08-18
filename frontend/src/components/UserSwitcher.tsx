import type { User } from "../types";

type Props = {
  users: User[];
  selectedWallet: string;
  onSelect: (walletName: string) => void;
};

export function UserSwitcher({ users, selectedWallet, onSelect }: Props) {
  return (
    <div className="toolbar">
      {users.map((user) => (
        <button
          key={user.id}
          className={user.wallet_name === selectedWallet ? "active" : ""}
          onClick={() => onSelect(user.wallet_name)}
        >
          {user.name}
        </button>
      ))}
    </div>
  );
}
