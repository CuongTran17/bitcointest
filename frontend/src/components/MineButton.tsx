type Props = {
  onMine: () => void;
};

export function MineButton({ onMine }: Props) {
  return <button onClick={onMine}>Mine 1 block</button>;
}
