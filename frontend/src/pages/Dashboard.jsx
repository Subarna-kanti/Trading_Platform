// src/pages/Dashboard.jsx
import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { getMyOrders, createOrder, cancelOrder } from "../api/orders";
import { getMyWallet } from "../api/wallets";
import { getMyTrades } from "../api/trades";
import { connectWebSocket, disconnectWebSocket } from "../api/websocket";
import { topupWallet, deductWallet, addAssetWallet, deductAssetWallet } from "../api/wallets";
import { getCurrentUser } from "../api/users";
import Wallet from "../components/Wallet";
import Trades from "../components/Trades";
import TopNav from "../components/TopNav";

export default function Dashboard() {
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

    // Redirect if no token
    useEffect(() => {
        if (!token) navigate("/login", { replace: true });
    }, [token, navigate]);

    // --- API fetchers ---
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
            // First, fetch current user info
            if (!mountedRef.current) return;

            // Fetch other data in parallel
            const ordersData = await getMyOrders(token);
            const walletData = await getMyWallet(token);
            const tradesData = await getMyTrades(token);
            const currentUser = await getCurrentUser(token);

            if (!mountedRef.current) return;

            setOrders(ordersData || []);
            setWallet(walletData || null);
            setTrades(tradesData || []);
            setUser(currentUser);
            setNewOrder((prev) => ({
                ...prev,
                user_id: currentUser.id,
            }));
            localStorage.setItem("user", JSON.stringify(currentUser));
            setErrorMsg("");
        } catch (err) {
            console.error(err);
            setErrorMsg("Failed to load data from server.");
        } finally {
            if (mountedRef.current) setLoading(false);
        }
    };

    // --- Order actions ---
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

    // --- Wallet actions ---
    const handleTopup = async () => {
        if (topupAmount <= 0) {
            alert("Enter a positive amount");
            return;
        }
        try {
            await topupWallet(topupAmount, token);
            setTopupAmount(0);
            fetchAllData();
        } catch (err) {
            alert("Failed to top-up wallet: " + (err.message || "Unknown error"));
        }
    };

    const handleDeduction = async () => {
        if (deductAmount <= 0) {
            alert("Enter a positive amount");
            return;
        }
        try {
            await deductWallet(topupAmount, token);
            setDeductAmount(0);
            fetchAllData();
        } catch (err) {
            alert("Failed to top-up wallet: " + (err.message || "Unknown error"));
        }
    };

    const handleAssetAddition = async () => {
        if (addAsset <= 0) {
            alert("Enter a positive amount");
            return;
        }
        try {
            await addAssetWallet(addAsset, token);
            setAssetAddition(0);
            fetchAllData();
        } catch (err) {
            alert("Failed to add asset in wallet: " + (err.message || "Unknown error"));
        }
    }

    const handleAssetDeduction = async () => {
        if (withdrawAsset <= 0) {
            alert("Enter a positive amount");
            return;
        }
        try {
            await deductAssetWallet(addAsset, token);
            setAssetReduction(0);
            fetchAllData();
        } catch (err) {
            alert("Failed to remove asset in wallet: " + (err.message || "Unknown error"));
        }
    }

    // --- WebSocket ---
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

    // Called by TopNav after logout
    const onLogout = () => {
        setOrders([]);
        setWallet(null);
        setTrades([]);
        setWsMessages([]);
        setUser(null)
    };

    return (
        <div>
            <TopNav onLogout={onLogout} />

            <div style={{ padding: "2rem" }}>
                <h2>Dashboard</h2>

                {!backendAlive && <div style={{ color: "red", marginBottom: 12 }}>{errorMsg}</div>}

                {loading ? (
                    <div>Loading data...</div>
                ) : (
                    <>
                        <Wallet wallet={wallet} />

                        {/* ✅ Top-up form */}
                        <div style={{ marginBottom: "1.5rem" }}>
                            <h3>Top-up Wallet</h3>
                            <input
                                type="number"
                                placeholder="Amount"
                                value={topupAmount}
                                onChange={(e) => setTopupAmount(Number(e.target.value))}
                                style={{ marginRight: "0.5rem" }}
                            />
                            <button onClick={handleTopup}>Top Up</button>
                        </div>

                        <div style={{ marginBottom: "1.5rem" }}>
                            <h3>Withdraw From Wallet</h3>
                            <input
                                type="number"
                                placeholder="Amount"
                                value={deductAmount}
                                onChange={(e) => setDeductAmount(Number(e.target.value))}
                                style={{ marginRight: "0.5rem" }}
                            />
                            <button onClick={handleDeduction}>Withdraw</button>
                        </div>

                        {/* ✅ Asset Top-up form */}
                        <div style={{ marginBottom: "1.5rem" }}>
                            <h3>Add Asset</h3>
                            <input
                                type="number"
                                placeholder="Amount"
                                value={addAsset}
                                onChange={(e) => setAssetAddition(Number(e.target.value))}
                                style={{ marginRight: "0.5rem" }}
                            />
                            <button onClick={handleAssetAddition}>Add BTC</button>
                        </div>

                        <div style={{ marginBottom: "1.5rem" }}>
                            <h3>Withdraw Asset</h3>
                            <input
                                type="number"
                                placeholder="Amount"
                                value={withdrawAsset}
                                onChange={(e) => setAssetReduction(Number(e.target.value))}
                                style={{ marginRight: "0.5rem" }}
                            />
                            <button onClick={handleAssetDeduction}>Withdraw BTC</button>
                        </div>


                        {/* Orders Section */}
                        <h3>Create Order</h3>
                        <select
                            value={newOrder.type}
                            onChange={(e) => setNewOrder({ ...newOrder, type: e.target.value })}
                        >
                            <option value="buy">Buy</option>
                            <option value="sell">Sell</option>
                        </select>
                        <select
                            value={newOrder.order_kind}
                            onChange={(e) => setNewOrder({ ...newOrder, order_kind: e.target.value })}
                        >
                            <option value="limit">Limit</option>
                            <option value="market">Market</option>
                        </select>
                        <input
                            type="number"
                            placeholder="Price"
                            value={newOrder.price}
                            onChange={(e) => setNewOrder({ ...newOrder, price: Number(e.target.value) })}
                        />
                        <input
                            type="number"
                            placeholder="Quantity"
                            value={newOrder.quantity}
                            onChange={(e) => setNewOrder({ ...newOrder, quantity: Number(e.target.value) })}
                        />
                        <button onClick={handleCreateOrder}>Place Order</button>

                        {/* My Orders */}
                        <h3>My Orders</h3>
                        {orders.length === 0 ? (
                            <div>No active orders</div>
                        ) : (
                            <ul>
                                {orders.map((o) => (
                                    <li key={o.id}>
                                        {o.type} {o.quantity} BTC @ {o.price} USD, status: {o.status}, remaining_asset: {o.remaining_quantity}
                                        <button onClick={() => handleCancelOrder(o.id)}>Cancel</button>
                                    </li>
                                ))}
                            </ul>
                        )}

                        <h3>My Trades</h3>
                        <Trades trades={trades} />

                        <h3>Live Updates</h3>
                        <ul>
                            {wsMessages.map((msg, i) => (
                                <li key={i}>{msg}</li>
                            ))}
                        </ul>
                    </>
                )}
            </div>
        </div>
    );
}