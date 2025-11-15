export function formatDistanceToNow(value: string | null): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);
  const delta = Date.now() - date.getTime();

  const minutes = Math.floor(delta / 60000);
  if (minutes < 1) return "только что";
  if (minutes < 60) return `${minutes} мин назад`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ч назад`;

  const days = Math.floor(hours / 24);
  return `${days} дн назад`;
}
