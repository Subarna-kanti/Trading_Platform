// src/components/Trades.jsx
export default function Trades({ trades }) {
  if (!trades) return null;
  if (!trades.length) return <div>No trades yet.</div>;
  return (
    <div style={{ marginTop: "1rem" }}>
      <ul>
        {trades.map((t) => (
          <li key={t.id}>
            {t.quantity} BTC @ {t.price} USD — {t.trade_type} to {t.client_name}
          </li>
        ))}
      </ul>
    </div>
  );
}
