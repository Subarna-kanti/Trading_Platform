export default function OrderBook({ orderBook }) {
  if (!orderBook) return <div>Loading order book...</div>;

  return (
    <div style={{ display: "flex", gap: "2rem", border: "1px solid gray", padding: "1rem", marginBottom: "1rem" }}>
      <div>
        <h3>Buy Orders</h3>
        <ul>
          {orderBook.buy_orders.map((o) => (
            <li key={o.order_id}>
              {o.remaining_quantity} @ {o.price}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3>Sell Orders</h3>
        <ul>
          {orderBook.sell_orders.map((o) => (
            <li key={o.order_id}>
              {o.remaining_quantity} @ {o.price}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
