import { useEffect, useState } from "react";
import { getMyWallet } from "../api/wallets";
import { connectWebSocket } from "../api/websocket";

export default function UserStatus({ token }) {
  const [wallet, setWallet] = useState(null);
  const [backendError, setBackendError] = useState(false);
  const [wsError, setWsError] = useState(false);

  // Fetch wallet
  const fetchWallet = async () => {
    try {
      const data = await getMyWallet(token);
      setWallet(data);
      setBackendError(false);
    } catch {
      setBackendError(true);
    }
  };

  useEffect(() => {
    fetchWallet();
    // WebSocket connection
    let ws;
    try {
      ws = connectWebSocket((msg) => console.log("WS Msg:", msg));
      setWsError(false);
    } catch {
      setWsError(true);
    }
    return () => ws?.close();
  }, []);

  return (
    <div>
      {backendError && <p style={{ color: "red" }}>Backend not reachable!</p>}
      {wsError && <p style={{ color: "red" }}>WebSocket not connected!</p>}

      {wallet && (
        <div>
          <h3>Wallet</h3>
          <p>Balance: {wallet.balance}</p>
          <p>Reserved: {wallet.reserved_balance}</p>
          <p>Holdings: {wallet.holdings} {wallet.asset_symbol}</p>
        </div>
      )}
    </div>
  );
}
