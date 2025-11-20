import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8300";

export default function LowConfidenceReview({ items = [] }) {
  // Normalize incoming data safely
  const normalizeItems = (list) => {
    if (!Array.isArray(list)) return [];

    return list.map((it, idx) => {
      const text = it.text ?? it.description ?? `item-${idx}`;

      // Category may be string OR object OR missing
      const predictedName =
        typeof it.category === "string"
          ? it.category
          : it.category?.name || it.predicted_category || "";

      const score =
        typeof it.score === "number"
          ? it.score
          : it.confidence ?? null;

      const entities = Array.isArray(it.entities) ? it.entities : [];

      return {
        id: it.id ?? idx,
        text,
        predicted: predictedName,
        score,
        entities,
        corrected: predictedName
      };
    });
  };

  const [edited, setEdited] = useState(normalizeItems(items));
  const [status, setStatus] = useState("");

  // Re-run normalization when new items arrive
  useEffect(() => {
    setEdited(normalizeItems(items));
  }, [items]);

  const updateField = (idx, val) => {
    setEdited((prev) => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], corrected: val };
      return copy;
    });
  };

  const submitCorrections = async () => {
    try {
      setStatus("Submitting corrections…");

      await axios.post(`${API_BASE}/api/low-confidence/submit/`, {
        items: edited.map((i) => ({
          text: i.text,
          corrected: i.corrected
        }))
      });

      setStatus("Corrections saved ✔️");
    } catch (err) {
      console.error("submitCorrections error:", err);
      setStatus("Failed to submit corrections");
    }
  };

  // Empty list case
  if (!edited.length) {
    return (
      <div style={{ padding: 20, border: "1px solid #ddd", borderRadius: 8 }}>
        <h3>Low Confidence – Review</h3>
        <p>No low-confidence items found.</p>
      </div>
    );
  }

  return (
    <div style={{ border: "1px solid #ddd", padding: 20, borderRadius: 8 }}>
      <h3>Low Confidence – Review Required</h3>
      <p>These items scored below the confidence threshold. Please correct them.</p>

      {edited.map((item, idx) => (
        <div
          key={item.id}
          style={{
            padding: 12,
            marginBottom: 14,
            background: "#f9fafb",
            borderRadius: 8,
            borderLeft: "4px solid #f87171"
          }}
        >
          <div style={{ marginBottom: 6 }}>
            <strong>Text:</strong> {item.text}
          </div>

          <div style={{ marginBottom: 6 }}>
            <strong>Predicted:</strong> {String(item.predicted)}{" "}
            {item.score !== null && `(${Number(item.score).toFixed(2)})`}
          </div>

          <label style={{ display: "block", marginTop: 8 }}>
            <strong>Corrected Category:</strong>
            <input
              type="text"
              value={item.corrected}
              onChange={(e) => updateField(idx, e.target.value)}
              style={{
                width: "100%",
                marginTop: 4,
                padding: 6,
                borderRadius: 6,
                border: "1px solid #ccc"
              }}
            />
          </label>
        </div>
      ))}

      <button
        onClick={submitCorrections}
        style={{
          padding: "8px 16px",
          marginTop: 12,
          background: "#2563eb",
          color: "#fff",
          border: "none",
          borderRadius: 6,
          cursor: "pointer"
        }}
      >
        Submit Corrections
      </button>

      {status && (
        <div style={{ marginTop: 12, fontStyle: "italic" }}>{status}</div>
      )}
    </div>
  );
}
