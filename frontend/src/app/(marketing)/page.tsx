import { Hero, Ecosystem, Problem, ProductThesis } from "@/components/marketing/home/hero-sections";
import { ArchitectureFlow, KillerDemo, EvidenceFirst, WorkOrderImpact } from "@/components/marketing/home/product-sections";
import { RiskIntelligence, DashboardPreview, AlertsAction, RoleSolutions, Industries } from "@/components/marketing/home/middle-sections";
import { SystemEcosystem, AITrust, Security, DataFreshness, HumanInTheLoop, ROI } from "@/components/marketing/home/trust-sections";
import { RoadmapArchitecture, PilotCTA } from "@/components/marketing/home/vision-sections";

export default function MarketingHome() {
  return (
    <>
      <Hero />
      <Ecosystem />
      <Problem />
      <ProductThesis />
      <ArchitectureFlow />
      <KillerDemo />
      <EvidenceFirst />
      <WorkOrderImpact />
      <RiskIntelligence />
      <DashboardPreview />
      <AlertsAction />
      <RoleSolutions />
      <Industries />
      <SystemEcosystem />
      <AITrust />
      <Security />
      <DataFreshness />
      <HumanInTheLoop />
      <ROI />
      <RoadmapArchitecture />
      <PilotCTA />
    </>
  );
}
