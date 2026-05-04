export function useProtection() {
  const setTP = async (symbol, price) => {
    try {
      const response = await fetch(`/api/protection/${symbol}/tp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ price }),
      });
      return await response.json();
    } catch (err) {
      console.error("[useProtection] setTP error:", err);
      return { ok: false, error: String(err) };
    }
  };

  const setSL = async (symbol, price) => {
    try {
      const response = await fetch(`/api/protection/${symbol}/sl`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ price }),
      });
      return await response.json();
    } catch (err) {
      console.error("[useProtection] setSL error:", err);
      return { ok: false, error: String(err) };
    }
  };

  return { setTP, setSL };
}
