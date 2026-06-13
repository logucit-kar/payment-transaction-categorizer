import React, { useEffect, useState } from "react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8300";

export default function TransactionList() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/api/transactions/`);
      setTransactions(res.data);
    } catch (err) {
      console.error("Failed to load transactions", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div style={{ padding: 20 }}>
      <h2>Transaction Records</h2>

      <div style={{ marginBottom: 20 }}>
        <a
          href={`${API_BASE}/api/transactions/export/csv/`}
          download
        >
          <button>Download CSV</button>
        </a>

        <a
          href={`${API_BASE}/api/transactions/export/json/`}
          download
          style={{ marginLeft: 10 }}
        >
          <button>Download JSON</button>
        </a>
      </div>

      {loading ? (
        <p>Loading...</p>
      ) : transactions.length === 0 ? (
        <p>No transactions found.</p>
      ) : (
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            marginTop: 10
          }}
        >
          <thead>
            <tr style={{ background: "#f4f4f4" }}>
              <th>Description</th>
              <th>Amount</th>
              <th>Date</th>
              <th>Predicted Category</th>
              <th>Score</th>
              <th>User Label</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx) => (
              <tr key={tx.id}>
                <td>{tx.description}</td>
                <td>{tx.amount}</td>
                <td>{tx.date}</td>
                <td>{tx.predicted_category}</td>
                <td>{tx.predicted_score}</td>
                <td>{tx.user_label}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
