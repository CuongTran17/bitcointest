type Props = {
  onMine: () => void;
};

export function MineButton({ onMine }: Props) {
  return (
    <button type="button" className="btn-secondary" onClick={onMine}>
      Mine 1 block
    </button>
  );
}
