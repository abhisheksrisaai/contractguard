# 📖 ContractGuard — User Manual

## A Simple Guide to Using ContractGuard

---

### 1. How to Access the App

1. Open your web browser (Chrome, Firefox, or Edge recommended)
2. Go to: **https://contractguard-beryl.vercel.app**
3. No sign-up, no login — the app is ready to use immediately

> 💡 **Tip:** Bookmark the URL for quick access later.

---

### 2. How to Upload a Contract

ContractGuard works with **PDF contracts only** (text-based PDFs, not scanned images).

1. On the home page, you'll see a large **upload zone** with a document icon
2. **Option A — Drag & Drop:** Drag your PDF file from your computer and drop it onto the upload zone
3. **Option B — Click:** Click the upload zone to browse and select your PDF file
4. A progress bar will show the upload status
5. Wait 30–60 seconds for the AI to analyze your contract

> ⚠️ **Important:**
> - File must be a **PDF** (`.pdf` extension)
> - Maximum file size: **10 MB**
> - The PDF must contain **selectable text** (not scanned images)
> - First analysis may take longer if the server was sleeping (cold start)

---

### 3. How to Read the Risk Analysis

Once analysis is complete, you'll see three sections:

#### 3A. Risk Dashboard (Top)

| Element | What It Means |
|---------|---------------|
| **Overall Risk Score** | A number from 0–100. Higher = riskier contract |
| **High Risk Count** | Clauses with serious problems — review carefully |
| **Medium Risk Count** | Clauses with minor concerns |
| **Low Risk Count** | Clauses that are close to fair standards |
| **Assessment Summary** | AI-written overview of the contract |

#### 3B. Clause Cards (Middle)

Each clause in your contract gets its own card:

- **Risk Badge** (colored tag):
  - 🔴 **HIGH** — Contains unfair or one-sided terms
  - 🟡 **MEDIUM** — Some deviation from fair standards
  - 🟢 **LOW** — Close to fair-market language

- **Risk Explanation:** Why this clause is flagged and what makes it risky

- **Suggested Alternative:** A fair version of the clause from our library of 20 fair contract templates

- **Comparison Notes:** How your clause compares to the fair standard

> 💡 **Tip:** Pay special attention to **HIGH** risk clauses — these are the ones you should negotiate with the other party.

#### 3C. Original Contract Text (Bottom)

The full extracted text of your contract is available for reference.

---

### 4. How to Use Q&A Chat

The Q&A feature lets you ask questions about your contract in plain English.

1. Scroll to the **Q&A Chat** section
2. Type your question in the input box (e.g., *"What is my notice period?"*)
3. Press **Enter** or click **Send**
4. The AI reads your contract and provides a direct answer

**Example questions you can ask:**

| Question | Purpose |
|----------|---------|
| "What is my notice period?" | Find specific clause details |
| "Are there any hidden penalties?" | Discover hidden fees/charges |
| "Can they fire me without notice?" | Understand termination rights |
| "Is the non-compete enforceable?" | Evaluate restriction fairness |
| "What happens to my benefits if I leave?" | Understand post-employment rights |
| "Compare my salary terms with standard practice" | Benchmark against norms |

> 💡 **Tip:** Be specific in your questions. The AI has read your full contract and can find relevant clauses.

---

### 5. How to Download the Report

1. Click the **"Download Report"** button (visible after analysis completes)
2. A PDF file will be generated and downloaded to your computer
3. Open the file — it contains:
   - Cover page with analysis date
   - Overall risk score and breakdown
   - Detailed analysis of each clause with risk levels
   - Suggested fair alternatives for risky clauses
   - Assessment summary

The report is professionally formatted — perfect for:
- Sharing with a lawyer for review
- Keeping for your records
- Using during contract negotiations

---

### 6. Frequently Asked Questions (FAQ)

#### Q: Is ContractGuard free?
**A:** Yes, completely free. No hidden costs, no premium tiers.

#### Q: Is my contract data safe?
**A:** Your contract is processed in memory and deleted after analysis. We do not store your contracts permanently. The service runs on secure cloud infrastructure (Render).

#### Q: What types of contracts can I analyze?
**A:** Currently optimized for employment agreements, consulting contracts, service agreements, and NDAs. The AI can analyze any English-language contract.

#### Q: How accurate is the analysis?
**A:** In our testing on 5 real-world contracts, the AI correctly identified 85% of risky clauses compared to manual lawyer review. Always use the results as guidance, not as legal advice.

#### Q: Can I analyze contracts in Hindi or other languages?
**A:** Currently English only. Support for Indian languages is planned for a future release.

#### Q: Why does the first upload take longer?
**A:** The backend server runs on a free cloud plan and "sleeps" after 15 minutes of inactivity. The first request wakes it up (30–60 seconds). Subsequent requests are faster (~30 seconds).

#### Q: What if the analysis says "No clauses could be identified"?
**A:** Your PDF may be a scanned image without selectable text. Try a text-based PDF or use OCR software to convert it first.

#### Q: Can I use this for legal advice?
**A:** No. ContractGuard is an educational and informational tool. It does not constitute legal advice. For binding legal opinions, consult a qualified lawyer.

#### Q: How do I report a bug or suggest a feature?
**A:** Open an issue on our GitHub repository: **github.com/abhisheksrisaai/contractguard**

---

### 7. Quick Reference Cheat Sheet

| Action | How |
|--------|-----|
| Upload PDF | Drag & drop or click upload zone |
| View risk score | Look at the dashboard card at top |
| Find risky clauses | Scroll for red 🔴 HIGH risk badges |
| See fair alternatives | Expand any clause card |
| Ask a question | Type in Q&A chat box + press Enter |
| Get PDF report | Click "Download Report" button |
| Start over | Refresh the page and upload a new PDF |

---

*Need help? Open an issue at github.com/abhisheksrisaai/contractguard*
