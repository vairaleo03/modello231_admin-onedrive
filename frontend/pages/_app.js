import "@/styles/globals.css";
import Layout from "../components/Layout";
import { ClerkProvider, useUser } from "@clerk/nextjs";
import { useRouter } from "next/router";
import { itIT } from '@clerk/localizations';
import { useEffect } from "react";

function PingOnLogin() {
  const { isSignedIn, user } = useUser();

  

  useEffect(() => {
    if (isSignedIn && user) {
      console.log('ruolo: ', user?.publicMetadata?.role);
      const payload = {
        user_id: user.id,
        email: user.emailAddresses[0]?.emailAddress,
        full_name: user.fullName,
      };
      fetch(`${process.env.NEXT_PUBLIC_BE}/ping`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      })
        .then((res) => res.json())
        .then((data) => console.log("BE:", data.message))
        .catch((err) => console.error("❌ Errore backend:", err));
    }
  }, [isSignedIn, user]);

  return null;
}

export default function App({ Component, pageProps }) {
  const router = useRouter();

  return (
    <ClerkProvider
      localization={itIT}
      navigate={(to) => router.push(to)}
      afterSignInUrl="/dashboard"
      afterSignUpUrl="/dashboard"
    >
      <Layout>
        <PingOnLogin />
        <Component {...pageProps} />
      </Layout>
    </ClerkProvider>
  );
}
