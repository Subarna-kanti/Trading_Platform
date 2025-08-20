// src/components/Wallet.jsx
export default function Wallet({ wallet }) {
  if (!wallet) return <div>Loading wallet...</div>;
  return (
    <div style={{ border: "1px solid #ddd", padding: "1rem", marginBottom: "1rem" }}>
      <h3>Wallet</h3>
      <div>Balance: {Number(wallet.balance).toFixed(2)} {wallet.currency || "USD"}</div>
      <div>Reserved Balance: {Number(wallet.reserved_balance).toFixed(2)} {wallet.currency || "USD"}</div>
      <div>Holdings: {Number(wallet.holdings).toFixed(3)} {wallet.asset_symbol || "BTC"}</div>
      <div> Reserved Holdings: {Number(wallet.reserved_holdings).toFixed(3)} {wallet.asset_symbol || "BTC"}</div>
    </div>
  );
}
