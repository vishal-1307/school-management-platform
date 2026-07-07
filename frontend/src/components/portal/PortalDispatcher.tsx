import { useEffect, useState } from "react";
import { getMe, portalHomeFor } from "../../lib/authStore";
import { Spinner } from "./kit";

export default function PortalDispatcher() {
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getMe(true).then((me) => {
      if (me) {
        window.location.replace(portalHomeFor(me.role));
      } else {
        setFailed(true);
      }
    });
  }, []);

  if (failed) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-4 text-center">
        <p className="font-extrabold text-slate-800">Could not verify your account.</p>
        <p className="text-sm text-slate-500 font-semibold max-w-sm">
          Your sign-in worked, but no matching user exists in the school system yet. Ask the
          school admin to create your login, or try again.
        </p>
        <a href="/sign-in" className="text-indigo-600 font-bold text-sm hover:underline">
          Back to sign in
        </a>
      </div>
    );
  }
  return (
    <div className="min-h-screen flex items-center justify-center">
      <Spinner />
    </div>
  );
}
