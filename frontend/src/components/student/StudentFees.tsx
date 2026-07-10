import { useCallback, useEffect, useState } from "react";
import { authFetch, openHtmlDocument } from "../../lib/api";
import PortalShell from "../portal/PortalShell";
import { Button, Spinner, formatDate, useToast } from "../portal/kit";

interface FeeItem {
  fee_structure_id: number;
  fee_head: string;
  term: string | null;
  amount: number;
  due_date: string;
  paid: number;
  balance: number;
}

interface Transaction {
  id: number;
  receipt_number: string;
  amount_paid: number;
  payment_mode: string;
  paid_at: string | null;
}

interface MyFees {
  items: FeeItem[];
  transactions: Transaction[];
}

interface RazorpayOrder {
  order_id: string;
  amount: number;
  currency: string;
  key_id: string;
  fee_head: string;
}

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open(): void };
  }
}

const rupees = (value: number) => `₹${value.toLocaleString("en-IN")}`;

function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

function FeesView() {
  const toast = useToast();
  const [data, setData] = useState<MyFees | null>(null);
  const [error, setError] = useState("");
  const [paying, setPaying] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await authFetch<MyFees>("/api/fees/my"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load fee status");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const payNow = async (item: FeeItem) => {
    setPaying(item.fee_structure_id);
    try {
      const order = await authFetch<RazorpayOrder>("/api/fees/razorpay/order", {
        method: "POST",
        body: { fee_structure_id: item.fee_structure_id },
      });
      const loaded = await loadRazorpayScript();
      if (!loaded || !window.Razorpay) {
        toast("Could not load the payment window — check your connection", "error");
        return;
      }
      const razorpay = new window.Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: "Knowledge Academy",
        description: order.fee_head,
        order_id: order.order_id,
        handler: async (response: {
          razorpay_order_id: string;
          razorpay_payment_id: string;
          razorpay_signature: string;
        }) => {
          try {
            const receipt = await authFetch<Transaction>("/api/fees/razorpay/verify", {
              method: "POST",
              body: {
                ...response,
                fee_structure_id: item.fee_structure_id,
                amount: order.amount / 100,
              },
            });
            toast(`Payment successful — receipt ${receipt.receipt_number}`);
            load();
          } catch (e) {
            toast(e instanceof Error ? e.message : "Payment verification failed", "error");
          }
        },
        theme: { color: "#4F46E5" },
      });
      razorpay.open();
    } catch (e) {
      // 503 = online payments not configured yet
      toast(e instanceof Error ? e.message : "Could not start payment", "error");
    } finally {
      setPaying(null);
    }
  };

  if (error)
    return <p className="text-sm font-semibold text-rose-700 bg-rose-50 rounded-xl px-4 py-3">{error}</p>;
  if (!data) return <Spinner />;

  const totalBalance = data.items.reduce((sum, item) => sum + item.balance, 0);

  return (
    <>
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 flex items-center justify-between">
        <p className="font-extrabold text-slate-800">Outstanding balance</p>
        <p className={`text-2xl font-extrabold font-heading ${totalBalance > 0 ? "text-rose-600" : "text-emerald-600"}`}>
          {rupees(totalBalance)}
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400">Fee heads</h2>
        {data.items.length === 0 && (
          <p className="text-sm text-slate-400 font-semibold">No fee structure defined for your class yet.</p>
        )}
        {data.items.map((item) => (
          <div
            key={item.fee_structure_id}
            className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 flex flex-wrap items-center gap-3"
          >
            <div className="flex-1 min-w-[180px]">
              <p className="font-extrabold text-slate-800">
                {item.fee_head} {item.term ? `(${item.term})` : ""}
              </p>
              <p className="text-xs text-slate-400 font-bold">Due {formatDate(item.due_date)}</p>
            </div>
            <div className="text-sm font-bold text-slate-600">
              {rupees(item.paid)} / {rupees(item.amount)}
            </div>
            {item.balance > 0 ? (
              <Button onClick={() => payNow(item)} disabled={paying !== null}>
                {paying === item.fee_structure_id ? "Opening…" : `Pay ${rupees(item.balance)}`}
              </Button>
            ) : (
              <span className="px-3 py-1 bg-emerald-50 text-emerald-700 rounded-lg text-xs font-bold uppercase">
                Paid
              </span>
            )}
          </div>
        ))}
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400">Payment history</h2>
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm divide-y divide-slate-50">
          {data.transactions.length === 0 && (
            <p className="px-4 py-6 text-sm text-slate-400 font-semibold">No payments yet.</p>
          )}
          {data.transactions.map((txn) => (
            <div key={txn.id} className="flex items-center gap-4 px-4 py-2.5 text-sm font-semibold">
              <span className="flex-1 text-slate-700">{txn.receipt_number}</span>
              <span className="text-slate-400 text-xs uppercase">{txn.payment_mode}</span>
              <span className="text-slate-400 text-xs">{txn.paid_at ? formatDate(txn.paid_at) : ""}</span>
              <span className="font-extrabold text-slate-800">{rupees(txn.amount_paid)}</span>
              <button
                type="button"
                className="px-2 py-2.5 -mx-2 rounded-lg text-indigo-600 font-bold hover:underline hover:bg-indigo-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                onClick={() =>
                  openHtmlDocument(`/api/fees/receipts/${txn.id}/html`).catch((e) =>
                    toast(e instanceof Error ? e.message : "Failed", "error"),
                  )
                }
              >
                Receipt
              </button>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

export default function StudentFees() {
  return (
    <PortalShell portal="student" title="Fee Status & Payments">
      <FeesView />
    </PortalShell>
  );
}
