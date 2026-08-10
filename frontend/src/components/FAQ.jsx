import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

const FAQ_ITEMS = [
  {
    q: 'How does ContractGuard work?',
    a: 'Upload your contract as a PDF. Our AI extracts every clause, classifies the contract type, validates the 5 Cs of enforceability (Capacity, Consent, Consideration, Clarity, Compliance), scores each clause for risk, benchmarks against 50 fair-clause templates, and produces a negotiation playbook — all in under 60 seconds.',
  },
  {
    q: 'What types of contracts can I analyze?',
    a: 'Employment contracts, supplier/vendor agreements, works/construction contracts, partner/reseller agreements, service agreements, NDAs, and purchase orders. Our auto-detection identifies the type automatically, or you can select it manually for more tailored results.',
  },
  {
    q: 'Is my document stored or shared?',
    a: 'No. Your document is processed entirely in-memory and deleted immediately after analysis. We do not store, share, or train on your contracts. Zero retention, zero logging of document content.',
  },
  {
    q: 'How accurate is the analysis?',
    a: 'Our AI (Llama 3.3 70B and Mixtral 8x7B) achieves ~85% risk detection accuracy validated against legal review benchmarks. It catches the patterns commercial lawyers look for — but it is not a replacement for a qualified attorney.',
  },
  {
    q: 'Is this legal advice?',
    a: 'No. ContractGuard is an informational tool for contract review assistance. It flags risks, suggests negotiation points, and highlights missing protections — but it does not constitute legal advice. Always consult a qualified attorney before signing.',
  },
  {
    q: 'Which AI models does ContractGuard use?',
    a: 'We use Groq\'s high-speed inference with Llama 3.3 70B (best quality) and Mixtral 8x7B (best for very long contracts). You choose the model, or stick with the default. All inference runs on Groq Cloud.',
  },
];

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState(null);

  return (
    <section id="faq" className="py-16 sm:py-20 px-4 sm:px-6 bg-[#0A0A0A]">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-10">
          <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-3">
            Frequently Asked Questions
          </h2>
          <p className="text-white/50 text-sm sm:text-base">
            Everything you need to know before uploading
          </p>
        </div>

        <div className="space-y-2.5">
          {FAQ_ITEMS.map((item, i) => (
            <div
              key={i}
              className="card overflow-hidden transition-all duration-200"
            >
              <button
                onClick={() => setOpenIndex(openIndex === i ? null : i)}
                className="w-full flex items-center justify-between px-5 py-4 text-left"
              >
                <span className="text-sm sm:text-base font-medium text-white pr-4">
                  {item.q}
                </span>
                {openIndex === i ? (
                  <ChevronUp className="w-4 h-4 text-white/40 shrink-0" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-white/40 shrink-0" />
                )}
              </button>
              {openIndex === i && (
                <div className="px-5 pb-4 animate-slide-up">
                  <p className="text-sm text-white/50 leading-relaxed">
                    {item.a}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
