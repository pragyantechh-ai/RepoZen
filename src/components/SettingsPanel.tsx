import { useState } from "react";
import {
  X,
  UserPlus,
  LogIn,
  Trash2,
  Info,
  LogOut,
  Loader2,
  ChevronLeft,
  Shield,
  Mail,
  User,
  Lock,
  Eye,
  EyeOff,
  Sparkles,
  Calendar,
  Github,
  Heart,
  Globe,
} from "lucide-react";
import { useAuth } from "../stores/authStore";
import {
  apiRegister,
  apiLogin,
  apiLogout,
  apiDeleteAccount,
} from "../services/auth_service";

type View = "menu" | "register" | "login" | "delete" | "about";

interface Props {
  open: boolean;
  onClose: () => void;
}

const SettingsPanel = ({ open, onClose }: Props) => {
  const { user, accessToken, isAuthenticated, setAuth, clearAuth } = useAuth();
  const [view, setView] = useState<View>("menu");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Form fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");

  const resetForm = () => {
    setEmail("");
    setPassword("");
    setDisplayName("");
    setConfirmPassword("");
    setError("");
    setSuccess("");
    setShowPassword(false);
    setShowConfirmPassword(false);
    setDeleteConfirm("");
  };

  const goTo = (v: View) => {
    resetForm();
    setView(v);
  };

  // ── Register ─────────────────────────────────────────────────
  const handleRegister = async () => {
    setError("");
    if (!displayName.trim()) return setError("Display name is required");
    if (!email.trim()) return setError("Email is required");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      return setError("Enter a valid email address");
    if (password.length < 8)
      return setError("Password must be at least 8 characters");
    if (password !== confirmPassword)
      return setError("Passwords do not match");

    setLoading(true);
    try {
      await apiRegister(email, password, displayName);
      setSuccess("Account created! You can now log in.");
      setTimeout(() => goTo("login"), 1500);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  // ── Login ────────────────────────────────────────────────────
  const handleLogin = async () => {
    setError("");
    if (!email.trim() || !password)
      return setError("Email and password required");

    setLoading(true);
    try {
      const res = await apiLogin(email, password);
      setAuth(res.user, res.access_token, res.refresh_token);
      setSuccess("Welcome back!");
      setTimeout(() => goTo("menu"), 1000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  // ── Logout ───────────────────────────────────────────────────
  const handleLogout = async () => {
    setLoading(true);
    try {
      if (accessToken) await apiLogout(accessToken);
    } catch {
      // ignore
    } finally {
      clearAuth();
      setLoading(false);
      goTo("menu");
    }
  };

  // ── Delete account ───────────────────────────────────────────
  const handleDelete = async () => {
    setError("");
    if (deleteConfirm !== "DELETE") return setError('Type "DELETE" to confirm');

    setLoading(true);
    try {
      if (accessToken) await apiDeleteAccount(accessToken);
      clearAuth();
      setSuccess("Account deleted.");
      setTimeout(() => goTo("menu"), 1500);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Deletion failed");
    } finally {
      setLoading(false);
    }
  };

  // ── Key handler for forms ────────────────────────────────────
  const handleKeyDown =
    (action: () => void) => (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !loading) action();
    };

  if (!open) return null;

  // ── Shared styles ──────────────────────────────────────────
  const inputClass =
    "w-full px-4 py-3 rounded-xl text-sm text-foreground placeholder:text-gray-500 outline-none transition-all duration-200 focus:ring-2 focus:ring-purple-500/40";
  const inputStyle = {
    background: "hsla(228,20%,10%,0.6)",
    border: "1px solid hsla(228,15%,22%,0.3)",
  };
  const btnPrimary =
    "w-full py-3 rounded-xl text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className="relative w-full max-w-md mx-4 rounded-2xl overflow-hidden animate-fade-in max-h-[90vh] flex flex-col"
        style={{
          background: "hsla(228,20%,8%,0.95)",
          border: "1px solid hsla(228,15%,22%,0.3)",
          backdropFilter: "blur(40px)",
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4 shrink-0"
          style={{ borderBottom: "1px solid hsla(228,15%,22%,0.2)" }}
        >
          <div className="flex items-center gap-3">
            {view !== "menu" && (
              <button
                onClick={() => goTo("menu")}
                className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-white/5 transition-colors"
              >
                <ChevronLeft className="h-4 w-4 text-gray-400" />
              </button>
            )}
            <h2 className="text-base font-semibold text-foreground">
              {view === "menu" && "Settings"}
              {view === "register" && "Create Account"}
              {view === "login" && "Log In"}
              {view === "delete" && "Delete Account"}
              {view === "about" && "About"}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-white/5 transition-colors"
          >
            <X className="h-4 w-4 text-gray-400" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 overflow-y-auto">
          {/* ── Error / Success toasts ────────────────────── */}
          {error && (
            <div
              className="mb-4 px-4 py-3 rounded-xl text-sm text-red-300"
              style={{
                background: "hsla(0,80%,40%,0.12)",
                border: "1px solid hsla(0,80%,40%,0.25)",
              }}
            >
              {error}
            </div>
          )}
          {success && (
            <div
              className="mb-4 px-4 py-3 rounded-xl text-sm text-green-300"
              style={{
                background: "hsla(140,60%,35%,0.12)",
                border: "1px solid hsla(140,60%,35%,0.25)",
              }}
            >
              {success}
            </div>
          )}

          {/* ═══════ MENU ═══════════════════════════════════ */}
          {view === "menu" && (
            <div className="space-y-2">
              {isAuthenticated && user && (
                <div
                  className="mb-4 p-4 rounded-xl flex items-center gap-3"
                  style={{
                    background:
                      "linear-gradient(135deg, hsla(250,80%,65%,0.1), hsla(200,80%,55%,0.08))",
                    border: "1px solid hsla(250,80%,65%,0.15)",
                  }}
                >
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
                    <User className="h-5 w-5 text-white" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground truncate">
                      {user.display_name}
                    </p>
                    <p className="text-xs text-gray-400 truncate">
                      {user.email}
                    </p>
                  </div>
                  <Shield className="h-4 w-4 text-green-400 shrink-0" />
                </div>
              )}

              {!isAuthenticated ? (
                <>
                  <button
                    onClick={() => goTo("register")}
                    className="w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm text-gray-200 hover:bg-white/5 transition-colors"
                  >
                    <UserPlus className="h-4 w-4 text-purple-400" />
                    Create Account
                  </button>
                  <button
                    onClick={() => goTo("login")}
                    className="w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm text-gray-200 hover:bg-white/5 transition-colors"
                  >
                    <LogIn className="h-4 w-4 text-blue-400" />
                    Log In
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={handleLogout}
                    disabled={loading}
                    className="w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm text-gray-200 hover:bg-white/5 transition-colors disabled:opacity-50"
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 text-yellow-400 animate-spin" />
                    ) : (
                      <LogOut className="h-4 w-4 text-yellow-400" />
                    )}
                    {loading ? "Logging out…" : "Log Out"}
                  </button>
                  <button
                    onClick={() => goTo("delete")}
                    className="w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm text-red-400 hover:bg-red-500/5 transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete Account
                  </button>
                </>
              )}

              <div
                className="my-2 h-px"
                style={{ background: "hsla(228,15%,22%,0.2)" }}
              />

              <button
                onClick={() => goTo("about")}
                className="w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm text-gray-200 hover:bg-white/5 transition-colors"
              >
                <Info className="h-4 w-4 text-gray-400" />
                About
              </button>
            </div>
          )}

          {/* ═══════ REGISTER ═══════════════════════════════ */}
          {view === "register" && (
            <div className="space-y-4" onKeyDown={handleKeyDown(handleRegister)}>
              {/* Decorative top icon */}
              <div className="flex justify-center mb-2">
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center"
                  style={{
                    background:
                      "linear-gradient(135deg, hsla(250,80%,65%,0.2), hsla(200,80%,55%,0.15))",
                    border: "1px solid hsla(250,80%,65%,0.2)",
                  }}
                >
                  <UserPlus className="h-6 w-6 text-purple-400" />
                </div>
              </div>
              <p className="text-center text-xs text-gray-400 mb-2">
                Create your RepoZen account to save history & preferences.
              </p>

              {/* Display name */}
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="Display Name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className={inputClass}
                  style={{ ...inputStyle, paddingLeft: "2.5rem" }}
                />
              </div>

              {/* Email */}
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputClass}
                  style={{ ...inputStyle, paddingLeft: "2.5rem" }}
                />
              </div>

              {/* Password */}
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Password (min 8 chars)"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputClass}
                  style={{
                    ...inputStyle,
                    paddingLeft: "2.5rem",
                    paddingRight: "2.5rem",
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>

              {/* Confirm password */}
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="Confirm Password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className={inputClass}
                  style={{
                    ...inputStyle,
                    paddingLeft: "2.5rem",
                    paddingRight: "2.5rem",
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>

              {/* Password strength indicator */}
              <div className="flex gap-1">
                {[1, 2, 3, 4].map((level) => (
                  <div
                    key={level}
                    className="h-1 flex-1 rounded-full transition-all duration-300"
                    style={{
                      background:
                        password.length >= level * 3
                          ? level <= 1
                            ? "hsla(0,80%,50%,0.6)"
                            : level <= 2
                            ? "hsla(40,80%,50%,0.6)"
                            : level <= 3
                            ? "hsla(60,80%,50%,0.6)"
                            : "hsla(140,60%,45%,0.6)"
                          : "hsla(228,15%,22%,0.3)",
                    }}
                  />
                ))}
              </div>

              {/* Submit */}
              <button
                onClick={handleRegister}
                disabled={loading}
                className={btnPrimary}
                style={{
                  background:
                    "linear-gradient(135deg, hsla(250,80%,65%,0.4), hsla(200,80%,55%,0.3))",
                  border: "1px solid hsla(250,80%,65%,0.3)",
                  color: "#e2e8f0",
                }}
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <UserPlus className="h-4 w-4" />
                )}
                {loading ? "Creating Account…" : "Create Account"}
              </button>

              {/* Already have account */}
              <p className="text-center text-xs text-gray-500">
                Already have an account?{" "}
                <button
                  onClick={() => goTo("login")}
                  className="text-purple-400 hover:text-purple-300 transition-colors underline underline-offset-2"
                >
                  Log in
                </button>
              </p>
            </div>
          )}

          {/* ═══════ LOGIN ══════════════════════════════════ */}
          {view === "login" && (
            <div className="space-y-4" onKeyDown={handleKeyDown(handleLogin)}>
              {/* Decorative top icon */}
              <div className="flex justify-center mb-2">
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center"
                  style={{
                    background:
                      "linear-gradient(135deg, hsla(200,80%,55%,0.2), hsla(250,80%,65%,0.15))",
                    border: "1px solid hsla(200,80%,55%,0.2)",
                  }}
                >
                  <LogIn className="h-6 w-6 text-blue-400" />
                </div>
              </div>
              <p className="text-center text-xs text-gray-400 mb-2">
                Welcome back! Log in to your account.
              </p>

              {/* Email */}
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputClass}
                  style={{ ...inputStyle, paddingLeft: "2.5rem" }}
                />
              </div>

              {/* Password */}
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputClass}
                  style={{
                    ...inputStyle,
                    paddingLeft: "2.5rem",
                    paddingRight: "2.5rem",
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>

              {/* Submit */}
              <button
                onClick={handleLogin}
                disabled={loading}
                className={btnPrimary}
                style={{
                  background:
                    "linear-gradient(135deg, hsla(200,80%,55%,0.4), hsla(250,80%,65%,0.3))",
                  border: "1px solid hsla(200,80%,55%,0.3)",
                  color: "#e2e8f0",
                }}
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <LogIn className="h-4 w-4" />
                )}
                {loading ? "Logging In…" : "Log In"}
              </button>

              {/* Don't have account */}
              <p className="text-center text-xs text-gray-500">
                Don't have an account?{" "}
                <button
                  onClick={() => goTo("register")}
                  className="text-blue-400 hover:text-blue-300 transition-colors underline underline-offset-2"
                >
                  Create one
                </button>
              </p>
            </div>
          )}

          {/* ═══════ DELETE ACCOUNT ══════════════════════════ */}
          {view === "delete" && (
            <div className="space-y-4">
              {/* Warning icon */}
              <div className="flex justify-center mb-2">
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center"
                  style={{
                    background: "hsla(0,80%,40%,0.15)",
                    border: "1px solid hsla(0,80%,40%,0.25)",
                  }}
                >
                  <Trash2 className="h-6 w-6 text-red-400" />
                </div>
              </div>

              <div
                className="p-4 rounded-xl text-sm text-red-200 space-y-2"
                style={{
                  background: "hsla(0,80%,40%,0.08)",
                  border: "1px solid hsla(0,80%,40%,0.2)",
                }}
              >
                <p className="font-semibold text-red-300">⚠ This action is irreversible</p>
                <ul className="list-disc list-inside text-xs text-red-300/80 space-y-1">
                  <li>Your account will be permanently deleted</li>
                  <li>All saved sessions and history will be lost</li>
                  <li>You will be logged out immediately</li>
                </ul>
              </div>

              {/* Logged-in user info */}
              {user && (
                <div
                  className="p-3 rounded-xl flex items-center gap-3"
                  style={{
                    background: "hsla(228,20%,10%,0.5)",
                    border: "1px solid hsla(228,15%,22%,0.2)",
                  }}
                >
                  <User className="h-4 w-4 text-gray-400" />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-gray-300 truncate">
                      {user.display_name}
                    </p>
                    <p className="text-xs text-gray-500 truncate">{user.email}</p>
                  </div>
                </div>
              )}

              {/* Confirmation input */}
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">
                  Type <span className="font-mono text-red-300 font-bold">DELETE</span> to
                  confirm
                </label>
                <input
                  type="text"
                  placeholder="DELETE"
                  value={deleteConfirm}
                  onChange={(e) => setDeleteConfirm(e.target.value)}
                  onKeyDown={handleKeyDown(handleDelete)}
                  className={inputClass}
                  style={{
                    ...inputStyle,
                    borderColor:
                      deleteConfirm === "DELETE"
                        ? "hsla(0,80%,50%,0.5)"
                        : undefined,
                  }}
                />
              </div>

              {/* Delete button */}
              <button
                onClick={handleDelete}
                disabled={loading || deleteConfirm !== "DELETE"}
                className={btnPrimary}
                style={{
                  background:
                    deleteConfirm === "DELETE"
                      ? "hsla(0,80%,45%,0.5)"
                      : "hsla(0,10%,30%,0.3)",
                  border: "1px solid hsla(0,80%,40%,0.3)",
                  color:
                    deleteConfirm === "DELETE" ? "#fca5a5" : "#6b7280",
                  cursor:
                    deleteConfirm !== "DELETE" ? "not-allowed" : "pointer",
                }}
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
                {loading ? "Deleting…" : "Permanently Delete Account"}
              </button>
            </div>
          )}

          {/* ═══════ ABOUT ══════════════════════════════════ */}
          {view === "about" && (
            <div className="space-y-5">
              {/* Logo / brand */}
              <div className="flex flex-col items-center gap-3 mb-2">
                <div
                  className="w-16 h-16 rounded-2xl flex items-center justify-center"
                  style={{
                    background:
                      "linear-gradient(135deg, hsla(250,80%,65%,0.25), hsla(200,80%,55%,0.2))",
                    border: "1px solid hsla(250,80%,65%,0.2)",
                  }}
                >
                  <Sparkles className="h-7 w-7 text-purple-400" />
                </div>
                <div className="text-center">
                  <h3 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-blue-400">
                    RepoZen
                  </h3>
                  <p className="text-xs text-gray-500 mt-0.5">v1.0.0</p>
                </div>
              </div>

              <p className="text-sm text-gray-300 text-center leading-relaxed">
                AI-powered repository analysis tool. Upload any repo and chat
                with an intelligent agent that understands your codebase
                inside-out.
              </p>

              {/* Feature cards */}
              <div className="grid grid-cols-2 gap-2">
                {[
                  {
                    icon: Globe,
                    label: "Multi-language",
                    desc: "Supports all major languages",
                    color: "purple",
                  },
                  {
                    icon: Shield,
                    label: "Secure",
                    desc: "JWT + Redis auth",
                    color: "blue",
                  },
                  {
                    icon: Sparkles,
                    label: "AI Chat",
                    desc: "Gemini-powered analysis",
                    color: "purple",
                  },
                  {
                    icon: Github,
                    label: "Git Ready",
                    desc: "URL or ZIP upload",
                    color: "blue",
                  },
                ].map((feat) => (
                  <div
                    key={feat.label}
                    className="p-3 rounded-xl"
                    style={{
                      background:
                        feat.color === "purple"
                          ? "hsla(250,80%,65%,0.06)"
                          : "hsla(200,80%,55%,0.06)",
                      border: `1px solid ${
                        feat.color === "purple"
                          ? "hsla(250,80%,65%,0.12)"
                          : "hsla(200,80%,55%,0.12)"
                      }`,
                    }}
                  >
                    <feat.icon
                      className={`h-4 w-4 mb-1.5 ${
                        feat.color === "purple"
                          ? "text-purple-400"
                          : "text-blue-400"
                      }`}
                    />
                    <p className="text-xs font-medium text-gray-200">
                      {feat.label}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">{feat.desc}</p>
                  </div>
                ))}
              </div>

              {/* Tech stack */}
              <div
                className="p-4 rounded-xl"
                style={{
                  background: "hsla(228,20%,10%,0.5)",
                  border: "1px solid hsla(228,15%,22%,0.2)",
                }}
              >
                <p className="text-xs font-semibold text-gray-300 mb-2">
                  Tech Stack
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {[
                    "React",
                    "TypeScript",
                    "FastAPI",
                    "Redis",
                    "Gemini AI",
                    "Tailwind",
                    "Zustand",
                    "Docker",
                  ].map((tech) => (
                    <span
                      key={tech}
                      className="px-2 py-1 rounded-md text-xs text-gray-300"
                      style={{
                        background: "hsla(228,15%,22%,0.3)",
                        border: "1px solid hsla(228,15%,22%,0.2)",
                      }}
                    >
                      {tech}
                    </span>
                  ))}
                </div>
              </div>

              {/* Timestamps for logged-in user */}
              {isAuthenticated && user && (
                <div
                  className="p-3 rounded-xl flex items-center gap-2"
                  style={{
                    background: "hsla(228,20%,10%,0.4)",
                    border: "1px solid hsla(228,15%,22%,0.15)",
                  }}
                >
                  <Calendar className="h-3.5 w-3.5 text-gray-500" />
                  <p className="text-xs text-gray-500">
                    Account created:{" "}
                    {new Date(user.created_at).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </p>
                </div>
              )}

              {/* Footer */}
              <div className="text-center">
                <p className="text-xs text-gray-600 flex items-center justify-center gap-1">
                  Made with <Heart className="h-3 w-3 text-red-400" /> by the
                  RepoZen team
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;