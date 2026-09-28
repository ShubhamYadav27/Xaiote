export const metadata = { title: "Privacy Policy | Xaiote" };

export default function PrivacyPage() {
  return (
    <div className="bg-transparent min-h-screen">
      <section className="bg-slate-950 pt-32 pb-24 text-center px-4">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">Privacy Policy</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">Last Updated: September 2026</p>
      </section>
      
      <section className="py-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="space-y-12 text-lg text-slate-700">
          
          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">1. Introduction</h2>
            <p className="mb-4">
              Welcome to Xaiote ("we," "our," or "us"). We are committed to protecting the privacy and security of the data entrusted to us. This Privacy Policy explains how we collect, use, process, and disclose information when you access or use our manufacturing intelligence platform, website, and related services (collectively, the "Services").
            </p>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">2. Information We Collect</h2>
            <p className="mb-4">
              We collect information to provide, improve, and secure our Services. The types of information we collect include:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Account Information:</strong> Name, email address, password, company name, and contact details provided during registration.</li>
              <li><strong>Usage Data:</strong> Information about how you interact with our platform, including access logs, device information, and IP addresses.</li>
              <li><strong>Customer-Submitted Data:</strong> Operational and manufacturing information submitted by authorized users of our customers (see Section 3).</li>
            </ul>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">3. Manufacturing and Operational Data</h2>
            <p className="mb-4">
              As a manufacturing intelligence platform, Xaiote processes operational data submitted by our customer users. This includes machinery logs, production schedules, maintenance reports, vendor information, and other industrial operations data. We process this data strictly on behalf of our customers in accordance with our terms of service.
            </p>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">4. WhatsApp Communications</h2>
            <p className="mb-4">
              For customers who enable the WhatsApp integration feature, Xaiote receives and processes messages sent to the designated business number.
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>We only process messages from phone numbers that have been explicitly authorized by the customer administrator.</li>
              <li>Unauthorized messages are immediately rejected and dropped.</li>
              <li>We extract operational evidence from these messages to generate actionable manufacturing insights.</li>
            </ul>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">5. How We Use Information</h2>
            <p className="mb-4">
              We use the collected information for the following purposes:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>To provide, operate, and maintain the Services.</li>
              <li>To extract insights and identify manufacturing events (e.g., machine failures, maintenance needs).</li>
              <li>To authenticate users and ensure strict multi-tenant data isolation.</li>
              <li>To communicate with you regarding security updates, technical notices, and administrative messages.</li>
            </ul>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">6. AI and LLM Processing</h2>
            <p className="mb-4">
              Xaiote utilizes Large Language Models (LLMs) to structure and analyze manufacturing data. 
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>We do <strong>not</strong> use your private operational data or communications to train base AI models.</li>
              <li>Data processed through LLM providers is handled via enterprise agreements ensuring data isolation and privacy.</li>
            </ul>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">7. Data Storage and Security</h2>
            <p className="mb-4">
              We implement industry-standard technical and organizational measures designed to secure your information. This includes encryption in transit (TLS) and at rest, secure credential management, role-based access control, and tenant-level data isolation. While we strive to protect your data, no system is entirely impenetrable, and we cannot guarantee absolute security.
            </p>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">8. Data Retention</h2>
            <p className="mb-4">
              We retain personal and operational data only for as long as necessary to fulfill the purposes outlined in this Privacy Policy, provide our Services, and comply with legal obligations. Upon termination of an enterprise agreement, customer data is securely deleted in accordance with our terms of service.
            </p>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">9. Data Sharing and Service Providers</h2>
            <p className="mb-4">
              We do not sell your personal or operational data. We may share information with trusted third-party service providers (such as cloud hosting providers, LLM API providers, and communication platforms like Meta/WhatsApp) strictly for the purpose of operating the Services. These providers are bound by confidentiality obligations.
            </p>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">10. Customer Data Ownership</h2>
            <p className="mb-4">
              Our customers retain full ownership of the operational and manufacturing data they submit to Xaiote. We act merely as a data processor for this information, deriving insights exclusively for the customer's benefit.
            </p>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">11. User Rights</h2>
            <p className="mb-4">
              Depending on your jurisdiction, you may have the right to access, correct, delete, or restrict the processing of your personal information. If you wish to exercise these rights, please contact us. Note that for data submitted by your employer, you may need to route your request through your company's designated administrator.
            </p>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">12. Cookies and Website Analytics</h2>
            <p className="mb-4">
              We may use cookies and similar tracking technologies on our public website to analyze traffic and improve user experience. You can instruct your browser to refuse all cookies or indicate when a cookie is being sent.
            </p>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">13. Children's Privacy</h2>
            <p className="mb-4">
              Our Services are intended for enterprise use and are not directed to individuals under the age of 18. We do not knowingly collect personal information from children.
            </p>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">14. Changes to This Policy</h2>
            <p className="mb-4">
              We may update this Privacy Policy from time to time to reflect changes in our practices or regulatory requirements. We will notify you of any material changes by posting the updated policy on this page and updating the "Last Updated" date.
            </p>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">15. Contact Information</h2>
            <p className="mb-4">
              If you have any questions or concerns about this Privacy Policy or our data practices, please contact us at:
            </p>
            <p className="font-medium">
              Email: <a href="mailto:privacy@xaiote.com" className="text-teal-600 hover:text-teal-500 underline">privacy@xaiote.com</a>
            </p>
          </div>

        </div>
      </section>
    </div>
  );
}
