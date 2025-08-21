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
    // ---------- state ----------
    const [orders, setOrders] = useState([]);
    const [wallet, setWallet] = useState(null);
    const [trades, setTrades] = useState([]);
    const [wsMessages, setWsMessages] = useState([]);
    const [backendAlive, setBackendAlive] = useState(true);
    const [loading, setLoading] = useState(true);
    const [errorMsg, setErrorMsg] = useState("");
    const [activeTab, setActiveTab] = useState("wallet");

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

    const getErrorMessage = (err) => {
        if (!err) return "Unknown error";

        // Axios style error with response
        if (err.response) {
            const data = err.response.data;
            if (data) {
                if (data.detail) return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
                if (data.message) return typeof data.message === "string" ? data.message : JSON.stringify(data.message);
            }
            return `HTTP ${err.response.status} - ${err.response.statusText || ""}`;
        }

        // Generic JS error
        if (err.message) return err.message;

        // Last resort: stringify the whole error safely
        try {
            return JSON.stringify(err, Object.getOwnPropertyNames(err));
        } catch {
            return "Unknown error";
        }
    };

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
            const [ordersData, walletData, tradesData, currentUser] = await Promise.all([
                getMyOrders(token),
                getMyWallet(token),
                getMyTrades(token),
                getCurrentUser(token),
            ]);
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
                setWsMessages((prev) => [msg, ...prev].slice(0, 50));
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
            alert("Failed to create order: " + (getErrorMessage(err) || "Unknown error"));
        }
    };

    const handleCancelOrder = async (id) => {
        try {
            await cancelOrder(id, token);
            fetchAllData();
        } catch (err) {
            alert("Failed to cancel order: " + (getErrorMessage(err) || "Unknown error"));
        }
    };

    const handleTopup = async () => {
        if (topupAmount <= 0) return alert("Enter a positive amount");
        try {
            await topupWallet(topupAmount, token);
            setTopupAmount(0);
            fetchAllData();
        } catch (err) {
            alert("Failed to top-up wallet: " + (getErrorMessage(err) || "Unknown error"));
        }
    };

    const handleDeduction = async () => {
        if (deductAmount <= 0) return alert("Enter a positive amount");
        try {
            await deductWallet(deductAmount, token);
            setDeductAmount(0);
            fetchAllData();
        } catch (err) {
            alert("Failed to withdraw wallet: " + (getErrorMessage(err) || "Unknown error"));
        }
    };

    const handleAssetAddition = async () => {
        if (addAsset <= 0) return alert("Enter a positive amount");
        try {
            await addAssetWallet(addAsset, token);
            setAssetAddition(0);
            fetchAllData();
        } catch (err) {
            alert("Failed to add asset: " + (getErrorMessage(err) || "Unknown error"));
        }
    };

    const handleAssetDeduction = async () => {
        if (withdrawAsset <= 0) return alert("Enter a positive amount");
        try {
            await deductAssetWallet(withdrawAsset, token);
            setAssetReduction(0);
            fetchAllData();
        } catch (err) {
            alert("Failed to withdraw asset: " + (getErrorMessage(err) || "Unknown error"));
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
                <h2 className="dashboard-title">Trading Dashboard</h2>

                {!backendAlive && <div className="backend-error">{errorMsg}</div>}

                {loading ? (
                    <div className="loading">Loading data...</div>
                ) : (
                    <div className="main-grid">
                        {/* Left Panel: Wallet + Orders + Trades (Tabs) */}
                        <div className="left-panel card">
                            <div className="tabs">
                                <button className={activeTab === "wallet" ? "active" : ""} onClick={() => setActiveTab("wallet")}>Wallet</button>
                                <button className={activeTab === "orders" ? "active" : ""} onClick={() => setActiveTab("orders")}>Orders</button>
                                <button className={activeTab === "trades" ? "active" : ""} onClick={() => setActiveTab("trades")}>Trades</button>
                            </div>

                            <div className="tab-content">
                                {activeTab === "wallet" && (
                                    <div>
                                        <Wallet wallet={wallet} />
                                        <div className="wallet-actions">
                                            <div>
                                                <input type="number" placeholder="Top-up Amount" value={topupAmount} onChange={(e) => setTopupAmount(Number(e.target.value))} />
                                                <button onClick={handleTopup}>Top Up</button>
                                            </div>
                                            <div>
                                                <input type="number" placeholder="Withdraw Amount" value={deductAmount} onChange={(e) => setDeductAmount(Number(e.target.value))} />
                                                <button onClick={handleDeduction}>Withdraw</button>
                                            </div>
                                            <div>
                                                <input type="number" placeholder="Add BTC" value={addAsset} onChange={(e) => setAssetAddition(Number(e.target.value))} />
                                                <button onClick={handleAssetAddition}>Add Asset</button>
                                            </div>
                                            <div>
                                                <input type="number" placeholder="Withdraw BTC" value={withdrawAsset} onChange={(e) => setAssetReduction(Number(e.target.value))} />
                                                <button onClick={handleAssetDeduction}>Withdraw Asset</button>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {activeTab === "orders" && (
                                    <div>
                                        <div className="order-form" style={{ marginBottom: "1rem" }}>
                                            <div
                                                className="order-form-inputs"
                                                style={{
                                                    display: "flex",
                                                    gap: "0.5rem",
                                                    alignItems: "flex-end",
                                                    width: "100%",
                                                }}
                                            >
                                                {/* Order Kind */}
                                                <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
                                                    <label style={{ fontSize: "0.8rem", color: "#555", marginBottom: "0.25rem" }}>Order Kind</label>
                                                    <select
                                                        value={newOrder.order_kind}
                                                        onChange={(e) => setNewOrder({ ...newOrder, order_kind: e.target.value })}
                                                    >
                                                        <option value="limit">Limit</option>
                                                        <option value="market">Market</option>
                                                    </select>
                                                </div>

                                                {/* Order Type */}
                                                <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
                                                    <label style={{ fontSize: "0.8rem", color: "#555", marginBottom: "0.25rem" }}>Type</label>
                                                    <select
                                                        value={newOrder.type}
                                                        onChange={(e) => setNewOrder({ ...newOrder, type: e.target.value })}
                                                    >
                                                        <option value="buy">Buy</option>
                                                        <option value="sell">Sell</option>
                                                    </select>
                                                </div>

                                                {/* Price */}
                                                <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
                                                    <label style={{ fontSize: "0.8rem", color: "#555", marginBottom: "0.25rem" }}>Price</label>
                                                    <input
                                                        type="number"
                                                        value={newOrder.price}
                                                        onChange={(e) => setNewOrder({ ...newOrder, price: Number(e.target.value) })}
                                                        min="0"
                                                        placeholder="0.00"
                                                    />
                                                </div>

                                                {/* Quantity */}
                                                <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
                                                    <label style={{ fontSize: "0.8rem", color: "#555", marginBottom: "0.25rem" }}>Quantity</label>
                                                    <input
                                                        type="number"
                                                        value={newOrder.quantity}
                                                        onChange={(e) => setNewOrder({ ...newOrder, quantity: Number(e.target.value) })}
                                                        min="0"
                                                        placeholder="0"
                                                    />
                                                </div>

                                                {/* Place Order Button */}
                                                <button
                                                    onClick={handleCreateOrder}
                                                    style={{ flex: "0 0 auto", height: "2.5rem", marginLeft: "0.25rem" }}
                                                >
                                                    Place Order
                                                </button>
                                            </div>
                                        </div>

                                        <h3>My Orders</h3>
                                        {orders.length === 0 ? (
                                            <div>No active orders</div>
                                        ) : (
                                            <table className="orders-table">
                                                <thead>
                                                    <tr>
                                                        <th>Type</th>
                                                        <th>Qty</th>
                                                        <th>Price</th>
                                                        <th>Status</th>
                                                        <th>Remain</th>
                                                        <th></th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {orders.map((o) => (
                                                        <tr key={o.id} className={o.type === "buy" ? "buy-row" : "sell-row"}>
                                                            <td>{o.type.toUpperCase()}</td>
                                                            <td>{o.quantity}</td>
                                                            <td>{o.price}</td>
                                                            <td>{o.status}</td>
                                                            <td>{o.remaining_quantity}</td>
                                                            <td>
                                                                <button className="cancel-btn" onClick={() => handleCancelOrder(o.id)}>
                                                                    Cancel
                                                                </button>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        )}
                                    </div>
                                )}



                                {activeTab === "trades" && (
                                    <Trades trades={trades} />
                                )}
                            </div>
                        </div>

                        {/* Right Panel: Live Updates */}
                        <div className="right-panel card">
                            <h3>📡 Live Updates</h3>
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
                                                    <table className="orders-table">
                                                        <thead>
                                                            <tr><th>Qty</th><th>Price</th><th>Total</th><th>Time</th></tr>
                                                        </thead>
                                                        <tbody>
                                                            {data.map((t, idx) => (
                                                                <tr key={idx}>
                                                                    <td>{t.quantity}</td>
                                                                    <td>{t.price}</td>
                                                                    <td>{t.total_amount}</td>
                                                                    <td>{new Date(t.created_at).toLocaleString()}</td>
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
