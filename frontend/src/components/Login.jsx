import { useState } from "react";
import { login, register, resendVerification, verifyEmail } from "../api.js";

// "login" | "register" | "verify"
export default function Login({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleLoginOrRegister(e) {
    e.preventDefault();
    setError("");
    setInfo("");
    setBusy(true);
    try {
      if (mode === "register") {
        await register(email, password);
        setMode("verify");
        setInfo("We sent a 4-digit code to your email. Enter it below to finish creating your account.");
      } else {
        const { access_token } = await login(email, password);
        onAuthenticated(access_token, email);
      }
    } catch (err) {
      // If login fails because the account was never verified, guide them there directly.
      if (err.message?.toLowerCase().includes("verify")) {
        setMode("verify");
        setError(err.message);
      } else {
        setError(err.message || "Something went wrong");
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleVerify(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const { access_token } = await verifyEmail(email, code);
      onAuthenticated(access_token, email);
    } catch (err) {
      setError(err.message || "Verification failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleResend() {
    setError("");
    setInfo("");
    try {
      await resendVerification(email);
      setInfo("A new code has been sent.");
    } catch (err) {
      setError(err.message || "Could not resend code");
    }
  }

  if (mode === "verify") {
    return (
      <div className="auth-shell">
        <form className="auth-card" onSubmit={handleVerify}>
          <h1>Check your email</h1>
          <p className="sub">Enter the 4-digit code sent to {email}.</p>

          {error && <div className="auth-error">{error}</div>}
          {info && <div className="auth-toggle" style={{ marginBottom: 14 }}>{info}</div>}

          <div className="field">
            <label htmlFor="code">Verification code</label>
            <input
              id="code"
              inputMode="numeric"
              pattern="[0-9]{4}"
              maxLength={4}
              required
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              placeholder="0000"
              style={{ letterSpacing: "6px", fontSize: 20, textAlign: "center" }}
            />
          </div>

          <button type="submit" className="btn-primary full-btn" disabled={busy || code.length !== 4}>
            {busy ? "Verifying…" : "Verify & continue"}
          </button>

          <div className="auth-toggle">
            Didn't get it?{" "}
            <button type="button" className="link-btn" onClick={handleResend}>
              Resend code
            </button>
          </div>
        </form>
      </div>
    );
  }

  return (
    <div className="auth-shell">
      <form className="auth-card" onSubmit={handleLoginOrRegister}>
        <h1>Docs Search</h1>
        <p className="sub">Semantic search &amp; Q&amp;A over your PDFs.</p>

        {error && <div className="auth-error">{error}</div>}

        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters"
          />
        </div>

        <button type="submit" className="btn-primary full-btn" disabled={busy}>
          {busy ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
        </button>

        <div className="auth-toggle">
          {mode === "login" ? (
            <>
              New here?{" "}
              <button type="button" className="link-btn" onClick={() => setMode("register")}>
                Create an account
              </button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button type="button" className="link-btn" onClick={() => setMode("login")}>
                Log in
              </button>
            </>
          )}
        </div>
      </form>
    </div>
  );
}
