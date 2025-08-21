// src/pages/Dashboard.jsx
import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { getMyOrders, createOrder, cancelOrder } from "../api/orders";
import { getMyWallet, topupWallet, deductWallet, addAssetWallet, deductAssetWallet } from "../api/wallets";
import { getMyTrades } from "../api/trades";
import { connectWebSocket, disconnectWebSocket } from "../api/websocket";
import { getCurrentUser } from "../api/users";
import Wallet from "../components/Wallet";
import Trades from "../components/Trades";
import TopNav from "../components/TopNav";
import "../styles/dashboard.css";

export default function Dashboard() {
    // ---------- state + refs ----------
    const [orders, setOrders] = useState([]);
    const [wallet, setWallet] = useState(null);
    const [trades, setTrades] = useState([]);
    const [wsMessages, setWsMessages] = useState([]);
    const [backendAlive, setBackendAlive] = useState(true);
    const [loading, setLoading] = useState(true);
    const [errorMsg, setErrorMsg] = useState("");
    const [newOrder, setNewOrder] = useState({ user_id: null, order_kind: "limit", type: "buy", price: 0, quantity: 0 });
    const [topupAmount, setTopupAmount] = useState(0);
    const [deductAmount, setDeductAmount] = useState(0);
    const [addAsset, setAssetAddition] = useState(0);
    const [withdrawAsset, setAssetReduction] = useState(0);
    const [user, setUser] = useState(null);

    const token = localStorage.getItem("token");
    const navigate = useNavigate();
    const wsRef = useRef(null);
    const mountedRef = useRef(true);

    // ---------- effects ----------
    useEffect(() => {
        if (!token) navigate("/login", { replace: true });
    }, [token, navigate]);

    const fetchBackendHealth = async () => {
        try {
            const res = await fetch("http://localhost:8000/health");
            if (!res.ok) throw new Error("Backend not responding");
            setBackendAlive(true);
        } catch (err) {
            console.error(err);
            setBackendAlive(false);
            setErrorMsg("Backend server is down!");
        }
    };

    const fetchAllData = async () => {
        setLoading(true);
        try {
            if (!mountedRef.current) return;
            const ordersData = await getMyOrders(token);
            const walletData = await getMyWallet(token);
            const tradesData = await getMyTrades(token);
            const currentUser = await getCurrentUser(token);

            if (!mountedRef.current) return;
            setOrders(ordersData || []);
            setWallet(walletData || null);
            setTrades(tradesData || []);
            setUser(currentUser);
            setNewOrder((prev) => ({ ...prev, user_id: currentUser.id }));
            localStorage.setItem("user", JSON.stringify(currentUser));
            setErrorMsg("");
        } catch (err) {
            console.error(err);
            setErrorMsg("Failed to load data from server.");
        } finally {
            if (mountedRef.current) setLoading(false);
        }
    };

    useEffect(() => {
        mountedRef.current = true;
        fetchBackendHealth();
        fetchAllData();

        const ws = connectWebSocket(
            token,
            (msg) => {
                if (!mountedRef.current) return;
                setWsMessages((prev) => [...prev, msg]);
                if (msg.includes("Wallet Update") || msg.includes("Order Book Update")) {
                    fetchAllData();
                }
            },
            () => console.log("WebSocket connected"),
            () => console.log("WebSocket disconnected"),
            (err) => console.error("WebSocket error:", err)
        );

        wsRef.current = ws;
        return () => {
            mountedRef.current = false;
            disconnectWebSocket();
        };
        // eslint-disable-next-line
    }, []);

    // ---------- handlers ----------
    const handleCreateOrder = async () => {
        try {
            await createOrder(newOrder, token);
            setNewOrder({ type: "buy", price: 0, quantity: 0, order_kind: "limit" });
            fetchAllData();
        } catch (err) {
            alert("Failed to create order: " + (err.message || "Unknown error"));
        }
    };

    const handleCancelOrder = async (id) => {
        try {
            await cancelOrder(id, token);
            fetchAllData();
        } catch (err) {
            alert("Failed to cancel order: " + (err.message || "Unknown error"));
        }
    };

    const handleTopup = async () => {
        if (topupAmount <= 0) return alert("Enter a positive amount");
        try {
            await topupWallet(topupAmount, token);
            setTopupAmount(0);
            fetchAllData();
        } catch (err) {
            alert("Failed to top-up wallet: " + (err.message || "Unknown error"));
        }
    };

    const handleDeduction = async () => {
        if (deductAmount <= 0) return alert("Enter a positive amount");
        try {
            await deductWallet(deductAmount, token);
            setDeductAmount(0);
            fetchAllData();
        } catch (err) {
            alert("Failed to withdraw wallet: " + (err.message || "Unknown error"));
        }
    };

    const handleAssetAddition = async () => {
        if (addAsset <= 0) return alert("Enter a positive amount");
        try {
            await addAssetWallet(addAsset, token);
            setAssetAddition(0);
            fetchAllData();
        } catch (err) {
            alert("Failed to add asset: " + (err.message || "Unknown error"));
        }
    };

    const handleAssetDeduction = async () => {
        if (withdrawAsset <= 0) return alert("Enter a positive amount");
        try {
            await deductAssetWallet(withdrawAsset, token);
            setAssetReduction(0);
            fetchAllData();
        } catch (err) {
            alert("Failed to withdraw asset: " + (err.message || "Unknown error"));
        }
    };

    const onLogout = () => {
        setOrders([]);
        setWallet(null);
        setTrades([]);
        setWsMessages([]);
        setUser(null);
    };

    // ---------- render ----------
    return (
        <div className="dashboard">
            <TopNav onLogout={onLogout} />
            <div className="dashboard-container">
                <h2 className="dashboard-title">Dashboard</h2>

                {!backendAlive && <div className="backend-error">{errorMsg}</div>}

                {loading ? (
                    <div className="loading">Loading data...</div>
                ) : (
                    <div className="grid-container">
                        {/* Wallet Section */}
                        <div className="wallet-section card">
                            <Wallet wallet={wallet} />
                            <div className="wallet-actions">
                                <div className="wallet-action">
                                    <h4>Top-up Wallet</h4>
                                    <input type="number" placeholder="Amount" value={topupAmount} onChange={(e) => setTopupAmount(Number(e.target.value))} />
                                    <button onClick={handleTopup}>Top Up</button>
                                </div>
                                <div className="wallet-action">
                                    <h4>Withdraw Wallet</h4>
                                    <input type="number" placeholder="Amount" value={deductAmount} onChange={(e) => setDeductAmount(Number(e.target.value))} />
                                    <button onClick={handleDeduction}>Withdraw</button>
                                </div>
                                <div className="wallet-action">
                                    <h4>Add Asset</h4>
                                    <input type="number" placeholder="Amount" value={addAsset} onChange={(e) => setAssetAddition(Number(e.target.value))} />
                                    <button onClick={handleAssetAddition}>Add BTC</button>
                                </div>
                                <div className="wallet-action">
                                    <h4>Withdraw Asset</h4>
                                    <input type="number" placeholder="Amount" value={withdrawAsset} onChange={(e) => setAssetReduction(Number(e.target.value))} />
                                    <button onClick={handleAssetDeduction}>Withdraw BTC</button>
                                </div>
                            </div>
                        </div>

                        {/* Orders Section */}
                        <div className="orders-section card">
                            <h3>Create Order</h3>
                            <div className="order-form">
                                <select value={newOrder.type} onChange={(e) => setNewOrder({ ...newOrder, type: e.target.value })}>
                                    <option value="buy">Buy</option>
                                    <option value="sell">Sell</option>
                                </select>
                                <select value={newOrder.order_kind} onChange={(e) => setNewOrder({ ...newOrder, order_kind: e.target.value })}>
                                    <option value="limit">Limit</option>
                                    <option value="market">Market</option>
                                </select>
                                <input type="number" placeholder="Price" value={newOrder.price} onChange={(e) => setNewOrder({ ...newOrder, price: Number(e.target.value) })} />
                                <input type="number" placeholder="Quantity" value={newOrder.quantity} onChange={(e) => setNewOrder({ ...newOrder, quantity: Number(e.target.value) })} />
                                <button onClick={handleCreateOrder}>Place Order</button>
                            </div>

                            <h3>My Orders</h3>
                            {orders.length === 0 ? (
                                <div>No active orders</div>
                            ) : (
                                <ul className="orders-list">
                                    {orders.map((o) => (
                                        <li key={o.id} className="order-item">
                                            {o.type.toUpperCase()} {o.quantity} BTC @ {o.price} USD, status: {o.status}, remaining: {o.remaining_quantity}
                                            <button className="cancel-btn" onClick={() => handleCancelOrder(o.id)}>Cancel</button>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>

                        {/* Trades Section */}
                        <div className="trades-section card">
                            <h3>My Trades</h3>
                            <Trades trades={trades} />
                        </div>

                        {/* Live Updates */}
                        <div className="live-section card">
                            <h3>Live Updates</h3>
                            <div className="live-updates-container scrollable">
                                {wsMessages.map((msg, i) => {
                                    try {
                                        if (msg.startsWith("Order Book Update:")) {
                                            const raw = msg.replace("Order Book Update: ", "");
                                            const data = JSON.parse(raw);
                                            return (
                                                <div key={i} className="live-card">
                                                    <strong>📘 Order Book Update:</strong>
                                                    <div className="orders-grid">
                                                        <div>
                                                            <h4>Buy Orders</h4>
                                                            <table className="orders-table">
                                                                <thead>
                                                                    <tr><th>Price</th><th>Qty</th><th>Type</th></tr>
                                                                </thead>
                                                                <tbody>
                                                                    {data.buy_orders?.map((o, idx) => (
                                                                        <tr key={idx}><td>{o.price}</td><td>{o.remaining_quantity}</td><td>{o.order_kind}</td></tr>
                                                                    ))}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                        <div>
                                                            <h4>Sell Orders</h4>
                                                            <table className="orders-table">
                                                                <thead>
                                                                    <tr><th>Price</th><th>Qty</th><th>Type</th></tr>
                                                                </thead>
                                                                <tbody>
                                                                    {data.sell_orders?.map((o, idx) => (
                                                                        <tr key={idx}><td>{o.price}</td><td>{o.remaining_quantity}</td><td>{o.order_kind}</td></tr>
                                                                    ))}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        } else if (msg.startsWith("Trade Book Update:")) {
                                            const raw = msg.replace("Trade Book Update: ", "");
                                            const data = JSON.parse(raw);
                                            return (
                                                <div key={i} className="live-card">
                                                    <strong>💹 Trade Executed:</strong>
                                                    <table className="trades-table">
                                                        <thead>
                                                            <tr><th>Qty</th><th>Price</th><th>Total</th><th>Time</th></tr>
                                                        </thead>
                                                        <tbody>
                                                            {data.map((t, idx) => (
                                                                <tr key={idx}>
                                                                    <td>{t.quantity}</td>
                                                                    <td>{t.price}</td>
                                                                    <td>{t.total_amount}</td>
                                                                    <td>{new Date(t.created_at).toLocaleTimeString()}</td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            );
                                        } else if (msg.startsWith("Wallet Update")) {
                                            return <div key={i} className="live-card">💰 {msg}</div>;
                                        } else {
                                            return <div key={i} className="live-card">🔔 {msg}</div>;
                                        }
                                    } catch {
                                        return <div key={i} className="live-card">⚠️ {msg}</div>;
                                    }
                                })}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

.dashboard-container {
    padding: 2rem;
}

.dashboard-title {
    font-size: 2rem;
    margin-bottom: 1.5rem;
    text-align: center;
}

.backend-error {
    color: red;
    margin-bottom: 1rem;
    text-align: center;
}

.grid-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 1.5rem;
}

.card {
    background: #1e1e2f;
    padding: 1rem;
    border-radius: 8px;
    color: #fff;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.wallet-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
    margin-top: 1rem;
}

.wallet-action h4 {
    margin: 0 0 0.25rem 0;
    font-size: 0.9rem;
}

.wallet-action input {
    width: 100%;
    padding: 0.4rem;
    margin-bottom: 0.25rem;
    border-radius: 4px;
    border: 1px solid #555;
    background: #2a2a3c;
    color: #fff;
}

.wallet-action button {
    width: 100%;
    padding: 0.5rem;
    border: none;
    border-radius: 4px;
    background: #00bfff;
    color: #fff;
    cursor: pointer;
}

.wallet-action button:hover {
    background: #009acd;
}

.order-form {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
    gap: 0.5rem;
    margin-bottom: 1rem;
}

.orders-list,
.live-messages {
    list-style: none;
    padding: 0;
    margin: 0;
}

.order-item {
    padding: 0.5rem;
    margin-bottom: 0.5rem;
    background: #2a2a3c;
    border-radius: 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.cancel-btn {
    background: #ff4c4c;
    border: none;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    color: #fff;
    cursor: pointer;
}

.cancel-btn:hover {
    background: #cc0000;
}

.live-section ul {
    max-height: 200px;
    overflow-y: auto;
}

.live-updates-container {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    max-height: 300px;
    overflow-y: auto;
}

.live-card {
    background: #2a2a3c;
    padding: 0.75rem;
    border-radius: 6px;
    color: #fff;
}

.orders-grid {
    display: flex;
    gap: 1rem;
}

.orders-grid div ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

.orders-grid div h4 {
    margin: 0 0 0.25rem 0;
    font-size: 0.9rem;
}

.orders-table,
.trades-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 0.5rem;
    font-size: 0.9rem;
}

.orders-table th,
.trades-table th,
.orders-table td,
.trades-table td {
    border: 1px solid #444;
    padding: 0.4rem 0.6rem;
    text-align: center;
}

.orders-table th,
.trades-table th {
    background: #333;
    color: #00bfff;
}

.orders-table tr:nth-child(even),
.trades-table tr:nth-child(even) {
    background: #2a2a3c;
}

.live-updates-container.scrollable {
    max-height: 250px;
    /* keeps it compact */
    overflow-y: auto;
    /* scroll inside only */
    padding-right: 6px;
}

Please improve the overall design of the application as per real time trading platform without changing the logics