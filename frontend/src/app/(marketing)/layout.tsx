import { Metadata } from "next";
import { Navbar } from "@/components/marketing/navbar";
import { Footer } from "@/components/marketing/footer";

export const metadata: Metadata = {
  title: "Xaiote — Manufacturing Intelligence for Production Risk",
  description: "Xaiote connects production data and shop-floor communication to identify root causes, affected work orders and production risk before they become delivery failures.",
};

import { AuthProvider } from "@/components/providers/AuthProvider";
import { PilotModal } from "@/components/marketing/PilotModal";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col min-h-screen pt-16">
      <AuthProvider>
        <Navbar />
      </AuthProvider>
      <main className="flex-grow">{children}</main>
      <Footer />
      <PilotModal />
    </div>
  );
}
