import {
  useEffect,
  useRef,
  useState
} from "react";

import "./App.css";


function App() {

  const [activePage, setActivePage] = useState("dashboard");

  const [documents, setDocuments] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [deletingDocumentId, setDeletingDocumentId] = useState(null);
  const [trashDocuments, setTrashDocuments] = useState([]);
  const [restoringDocumentId, setRestoringDocumentId] = useState(null);
  const [permanentlyDeletingDocumentId, setPermanentlyDeletingDocumentId] = useState(null);

  const [stats, setStats] = useState({
    documents: 0,
    chunks: 0,
    compliance_checks: 0
  });

  const [query, setQuery] = useState("");

  const [searchResults, setSearchResults] = useState([]);
  const [externalResults, setExternalResults] = useState([]);
  const [showSupportingEvidence, setShowSupportingEvidence] = useState(false);

  const [actualAirflow, setActualAirflow] = useState("");

  const [complianceResult, setComplianceResult] = useState(null);

  const [incidentDescription, setIncidentDescription] = useState("");

  const [incidentResult, setIncidentResult] = useState(null);

  const searchInputRef = useRef(null);


  // =========================
  // LOAD DOCUMENTS + STATS
  // =========================

  useEffect(() => {

    fetch("/api/documents")
      .then((response) => response.json())
      .then((data) => {
        setDocuments(data);
      })
      .catch((error) => {
        console.error(
          "Error fetching documents:",
          error
        );
      });


    fetch("/api/stats")
      .then((response) => response.json())
      .then((data) => {
        setStats(data);
      })
      .catch((error) => {
        console.error(
          "Error fetching stats:",
          error
        );
      });

    fetch("/api/trash")
      .then((response) => response.json())
      .then((data) => {
        setTrashDocuments(Array.isArray(data) ? data : []);
      })
      .catch((error) => {
        console.error(
          "Error fetching recycle bin:",
          error
        );
      });

  }, []);


  // =========================
  // CTRL + K SEARCH SHORTCUT
  // =========================

  useEffect(() => {

    const handleShortcut = (event) => {

      if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === "k"
      ) {

        event.preventDefault();

        setActivePage("dashboard");

        setTimeout(() => {
          searchInputRef.current?.focus();
        }, 0);

      }

    };


    window.addEventListener(
      "keydown",
      handleShortcut
    );


    return () => {

      window.removeEventListener(
        "keydown",
        handleShortcut
      );

    };

  }, []);


  // =========================
  // DOCUMENT UPLOAD
  // =========================

  const uploadDocument = async () => {
    if (!selectedFile) {
      setUploadMessage("Please select a PDF document first.");
      return;
    }

    if (
      selectedFile.type !== "application/pdf" &&
      !selectedFile.name.toLowerCase().endsWith(".pdf")
    ) {
      setUploadMessage("Only PDF documents are supported.");
      return;
    }

    setUploading(true);
    setUploadMessage("");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(
        "/api/documents/upload",
        {
          method: "POST",
          body: formData
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || "Upload failed.");
      }

      setUploadMessage(
        `✓ ${data.filename || selectedFile.name} uploaded successfully.`
      );
      setSelectedFile(null);

      const [documentsResponse, statsResponse] = await Promise.all([
        fetch("/api/documents"),
        fetch("/api/stats")
      ]);

      if (documentsResponse.ok) {
        const documentsData = await documentsResponse.json();
        setDocuments(Array.isArray(documentsData) ? documentsData : []);
      }

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }
    } catch (error) {
      console.error("Document upload error:", error);
      setUploadMessage(`Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };


  // =========================
  // RECYCLE BIN
  // =========================

  const deleteDocument = async (documentId, filename) => {
    const confirmed = window.confirm(
      `Move "${filename}" to the recycle bin?\n\nYou can restore it later from the Bin.`
    );

    if (!confirmed) {
      return;
    }

    setDeletingDocumentId(documentId);
    setUploadMessage("");

    try {
      const response = await fetch(
        `/api/documents/${documentId}`,
        {
          method: "DELETE"
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || data.message || "Delete failed."
        );
      }

      setDocuments((currentDocuments) =>
        currentDocuments.filter((document) => document.id !== documentId)
      );

      const trashResponse = await fetch(
        "/api/trash"
      );

      if (trashResponse.ok) {
        const trashData = await trashResponse.json();
        setTrashDocuments(Array.isArray(trashData) ? trashData : []);
      }

      setUploadMessage(`✓ ${filename} moved to the recycle bin.`);

      const statsResponse = await fetch(
        "/api/stats"
      );

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }
    } catch (error) {
      console.error("Document delete error:", error);
      setUploadMessage(`Delete failed: ${error.message}`);
    } finally {
      setDeletingDocumentId(null);
    }
  };


  const restoreDocument = async (documentId, filename) => {
    setRestoringDocumentId(documentId);
    setUploadMessage("");

    try {
      const response = await fetch(
        `/api/trash/${documentId}/restore`,
        {
          method: "POST"
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || data.message || "Restore failed."
        );
      }

      const [documentsResponse, trashResponse, statsResponse] =
        await Promise.all([
          fetch("/api/documents"),
          fetch("/api/trash"),
          fetch("/api/stats")
        ]);

      if (documentsResponse.ok) {
        const documentsData = await documentsResponse.json();
        setDocuments(Array.isArray(documentsData) ? documentsData : []);
      }

      if (trashResponse.ok) {
        const trashData = await trashResponse.json();
        setTrashDocuments(Array.isArray(trashData) ? trashData : []);
      }

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }

      setUploadMessage(`✓ ${filename} restored successfully.`);
    } catch (error) {
      console.error("Document restore error:", error);
      setUploadMessage(`Restore failed: ${error.message}`);
    } finally {
      setRestoringDocumentId(null);
    }
  };


  const permanentlyDeleteDocument = async (documentId, filename) => {
    const confirmed = window.confirm(
      `PERMANENTLY DELETE "${filename}"?\n\nThis cannot be undone.`
    );

    if (!confirmed) {
      return;
    }

    setPermanentlyDeletingDocumentId(documentId);
    setUploadMessage("");

    try {
      const response = await fetch(
        `/api/trash/${documentId}`,
        {
          method: "DELETE"
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || data.message || "Permanent delete failed."
        );
      }

      setTrashDocuments((currentDocuments) =>
        currentDocuments.filter((document) => document.id !== documentId)
      );

      setUploadMessage(`✓ ${filename} permanently deleted.`);

      const statsResponse = await fetch(
        "/api/stats"
      );

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }
    } catch (error) {
      console.error("Permanent delete error:", error);
      setUploadMessage(`Permanent delete failed: ${error.message}`);
    } finally {
      setPermanentlyDeletingDocumentId(null);
    }
  };




  // =========================
  // SEARCH
  // =========================

const searchDocuments = async () => {

  if (!query.trim()) {
    return;
  }

  setShowSupportingEvidence(false);

  try {

    const externalQuery = `mining ${query.trim()}`;

    const [documentResponse, externalResponse] =
      await Promise.allSettled([

        fetch(
          `/api/search?query=${encodeURIComponent(
            query
          )}`
        ),

        fetch(
          `/api/external-search?query=${encodeURIComponent(
            externalQuery
          )}`
        )

      ]);


    if (documentResponse.status === "fulfilled") {

      const documentData =
        await documentResponse.value.json();

      setSearchResults(
        Array.isArray(documentData)
          ? documentData
          : []
      );

    } else {

      console.error(
        "Regulatory search failed:",
        documentResponse.reason
      );

      setSearchResults([]);

    }


    if (externalResponse.status === "fulfilled") {

      const externalData =
        await externalResponse.value.json();

      setExternalResults(
        Array.isArray(externalData)
          ? externalData
          : []
      );

    } else {

      console.error(
        "External search failed:",
        externalResponse.reason
      );

      setExternalResults([]);

    }


    setActivePage("search");

  } catch (error) {

    console.error(
      "Error performing search:",
      error
    );

  }

};


  // =========================
  // COMPLIANCE CHECK
  // =========================

  const checkCompliance = () => {

    if (!actualAirflow) {
      return;
    }

    if (documents.length === 0) {
      setComplianceResult({
        result: "ERROR",
        severity: "HIGH",
        message: "No regulatory document is available for compliance checking."
      });
      return;
    }


    fetch(
      "/api/compliance/check",
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json"
        },

        body: JSON.stringify({
          document_id: documents[0].id,
          actual_airflow: Number(actualAirflow)
        })

      }
    )
      .then((response) => response.json())
      .then((data) => {

        setComplianceResult(data);

      })
      .catch((error) => {

        console.error(
          "Error checking compliance:",
          error
        );

      });

  };


  // =========================
  // INCIDENT CLASSIFICATION
  // =========================

  const classifyIncident = () => {

    if (!incidentDescription.trim()) {
      return;
    }


    fetch(
      "/api/incidents/classify",
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json"
        },

        body: JSON.stringify({
          description: incidentDescription
        })

      }
    )
      .then((response) => response.json())
      .then((data) => {

        setIncidentResult(data);

      })
      .catch((error) => {

        console.error(
          "Error classifying incident:",
          error
        );

      });

  };


  const uniqueSearchResults = searchResults.filter(
    (result, index, self) =>
      index ===
      self.findIndex(
        (item) =>
          item.content?.trim().toLowerCase() ===
          result.content?.trim().toLowerCase()
      )
  );

  const primaryResult = uniqueSearchResults[0];

  const supportingResults = uniqueSearchResults.slice(1);

  return (

    <div className="app">


      {/* =========================
          SIDEBAR
      ========================= */}

      <aside className="sidebar">

        <h1>
          MineSafe
        </h1>


        <p className="sidebar-subtitle">
          Mining Safety & Engineering
          <br />
          Compliance System
        </p>


        <button
          className={
            activePage === "dashboard"
              ? "nav-button active"
              : "nav-button"
          }
          onClick={() =>
            setActivePage("dashboard")
          }
        >
          Dashboard
        </button>


        <button
          className={
            activePage === "documents"
              ? "nav-button active"
              : "nav-button"
          }
          onClick={() =>
            setActivePage("documents")
          }
        >
          Documents
        </button>


        <button
          className={
            activePage === "bin"
              ? "nav-button active"
              : "nav-button"
          }
          onClick={() =>
            setActivePage("bin")
          }
        >
          Bin
        </button>


        <button
          className={
            activePage === "search"
              ? "nav-button active"
              : "nav-button"
          }
          onClick={() =>
            setActivePage("search")
          }
        >
          Search
        </button>


        <button
          className={
            activePage === "compliance"
              ? "nav-button active"
              : "nav-button"
          }
          onClick={() =>
            setActivePage("compliance")
          }
        >
          Compliance
        </button>


        <button
          className={
            activePage === "incidents"
              ? "nav-button active"
              : "nav-button"
          }
          onClick={() =>
            setActivePage("incidents")
          }
        >
          Incidents
        </button>

      </aside>


      {/* =========================
          MAIN CONTENT
      ========================= */}

      <main className="main-content">


        {/* =========================
            DASHBOARD
        ========================= */}

        {activePage === "dashboard" && (

          <>

            <h2>
              Dashboard
            </h2>


            <p>
              Mining Safety & Engineering
              Compliance System
            </p>


            {/* =========================
                MAIN SEARCH
            ========================= */}

            <div className="dashboard-search">

              <input
                ref={searchInputRef}
                type="text"
                placeholder="Search safety regulations..."
                value={query}
                onChange={(event) =>
                  setQuery(event.target.value)
                }
                onKeyDown={(event) => {

                  if (event.key === "Enter") {
                    searchDocuments();
                  }

                }}
              />


              <button
                onClick={searchDocuments}
              >
                Search
              </button>

            </div>


            {/* =========================
                QUICK ACTIONS
            ========================= */}

            <div className="quick-actions">

              <h3>
                Quick Actions
              </h3>


              <div className="quick-action-buttons">

                <button
                  onClick={() =>
                    setActivePage("search")
                  }
                >
                  Search Regulations
                </button>


                <button
                  onClick={() =>
                    setActivePage("compliance")
                  }
                >
                  Check Compliance
                </button>


                <button
                  onClick={() =>
                    setActivePage("incidents")
                  }
                >
                  Analyze Incident
                </button>

              </div>

            </div>


            {/* =========================
                STATISTICS
            ========================= */}

            <div className="stats">


              <div className="stat-card">

                <h3>
                  Documents
                </h3>

                <strong>
                  {stats.documents}
                </strong>

                <p>
                  Regulatory sources
                </p>

              </div>


              <div className="stat-card">

                <h3>
                  Indexed Chunks
                </h3>

                <strong>
                  {stats.chunks}
                </strong>

                <p>
                  Searchable evidence
                </p>

              </div>


              <div className="stat-card">

                <h3>
                  Compliance Checks
                </h3>

                <strong>
                  {stats.compliance_checks}
                </strong>

                <p>
                  Recorded evaluations
                </p>

              </div>


              <div className="stat-card">

                <h3>
                  Retrieval
                </h3>

                <strong>
                  TF-IDF
                </strong>

                <p>
                  Active retrieval engine
                </p>

              </div>

            </div>


            {/* =========================
                SAFETY DOMAINS
            ========================= */}

            <div className="safety-domains">

              <h2>
                Safety Domains
              </h2>


              <div className="domain-grid">


                <div className="domain-card">

                  <h3>
                    Ventilation Safety
                  </h3>

                  <p>
                    Airflow and ventilation
                    requirements
                  </p>

                  <span>
                    Active
                  </span>

                </div>


                <div className="domain-card">

                  <h3>
                    Electrical Safety
                  </h3>

                  <p>
                    Electrical equipment
                    and safety requirements
                  </p>

                  <span>
                    Extensible
                  </span>

                </div>


                <div className="domain-card">

                  <h3>
                    Dust & Air Quality
                  </h3>

                  <p>
                    Dust exposure and
                    air-quality requirements
                  </p>

                  <span>
                    Extensible
                  </span>

                </div>


                <div className="domain-card">

                  <h3>
                    Fire & Explosion Safety
                  </h3>

                  <p>
                    Fire prevention and
                    hazard requirements
                  </p>

                  <span>
                    Extensible
                  </span>

                </div>


                <div className="domain-card">

                  <h3>
                    Workplace Safety
                  </h3>

                  <p>
                    Inspections, PPE and
                    operational safety
                  </p>

                  <span>
                    Extensible
                  </span>

                </div>


                <div className="domain-card">

                  <h3>
                    Environmental Safety
                  </h3>

                  <p>
                    Environmental compliance
                    requirements
                  </p>

                  <span>
                    Extensible
                  </span>

                </div>

              </div>

            </div>

          </>

        )}


        {/* =========================
            DOCUMENTS
        ========================= */}

        {activePage === "documents" && (

          <section>

            <div className="page-header">
              <div>
                <span className="page-label">
                  DOCUMENT MANAGEMENT
                </span>

                <h2>
                  Regulatory Documents
                </h2>

                <p>
                  Upload and manage the regulatory sources indexed by MineSafe.
                </p>
              </div>
            </div>


            {/* =========================
                DOCUMENT UPLOAD
            ========================= */}

            <div
              className="document-upload-card"
              style={{
                background: "#ffffff",
                border: "1px solid #dbe3ec",
                borderRadius: "16px",
                padding: "24px",
                marginTop: "24px",
                boxShadow: "0 6px 20px rgba(15, 23, 42, 0.06)"
              }}
            >

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "16px",
                  flexWrap: "wrap",
                  marginBottom: "18px"
                }}
              >
                <div>
                  <span className="result-label">
                    ADD REGULATORY SOURCE
                  </span>

                  <h3 style={{ marginTop: "7px", marginBottom: "5px" }}>
                    Upload a safety PDF
                  </h3>

                  <p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
                    The document will be processed and indexed for regulatory search.
                  </p>
                </div>

                <span className="verified-badge">
                  PDF ONLY
                </span>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  flexWrap: "wrap"
                }}
              >

                <label
                  htmlFor="document-file"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "11px 16px",
                    border: "1px solid #cbd5e1",
                    borderRadius: "9px",
                    background: "#f8fafc",
                    fontWeight: 700,
                    cursor: "pointer",
                    fontSize: "13px"
                  }}
                >
                  Choose PDF
                </label>

                <input
                  id="document-file"
                  type="file"
                  accept=".pdf,application/pdf"
                  style={{ display: "none" }}
                  onChange={(event) => {
                    setSelectedFile(event.target.files?.[0] || null);
                    setUploadMessage("");
                  }}
                />

                <button
                  onClick={uploadDocument}
                  disabled={!selectedFile || uploading}
                  style={{
                    padding: "11px 20px",
                    borderRadius: "9px",
                    border: "none",
                    fontWeight: 700,
                    cursor:
                      selectedFile && !uploading
                        ? "pointer"
                        : "not-allowed",
                    opacity:
                      selectedFile && !uploading
                        ? 1
                        : 0.55
                  }}
                >
                  {uploading ? "Uploading..." : "Upload Document"}
                </button>

                {selectedFile && (
                  <span
                    style={{
                      fontSize: "13px",
                      color: "#334155",
                      overflowWrap: "anywhere"
                    }}
                  >
                    {selectedFile.name}
                  </span>
                )}

              </div>

              {uploadMessage && (
                <p
                  style={{
                    marginTop: "14px",
                    marginBottom: 0,
                    fontSize: "13px",
                    fontWeight: 600,
                    color: uploadMessage.startsWith("✓")
                      ? "#0f766e"
                      : "#b91c1c"
                  }}
                >
                  {uploadMessage}
                </p>
              )}

            </div>


            {/* =========================
                DOCUMENT LIBRARY
            ========================= */}

            <div style={{ marginTop: "28px" }}>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "end",
                  gap: "12px",
                  flexWrap: "wrap",
                  marginBottom: "14px"
                }}
              >
                <div>
                  <span className="page-label">
                    INDEXED SOURCES
                  </span>

                  <h3 style={{ marginTop: "6px", marginBottom: 0 }}>
                    Document Library
                  </h3>
                </div>

                <span style={{ color: "#64748b", fontSize: "13px" }}>
                  {documents.length} source{documents.length === 1 ? "" : "s"} indexed
                </span>
              </div>

              {documents.length === 0 ? (

                <div className="empty-search-state">
                  <div className="empty-icon">
                    📄
                  </div>

                  <h3>
                    No documents found
                  </h3>

                  <p>
                    Upload a regulatory PDF above to build the MineSafe knowledge base.
                  </p>
                </div>

              ) : (

                <div className="document-grid">

                  {documents.map((document) => (

                    <div
                      className="document-card"
                      key={document.id}
                      style={{
                        background: "#ffffff",
                        border: "1px solid #dbe3ec",
                        borderRadius: "14px",
                        padding: "20px",
                        boxShadow: "0 4px 14px rgba(15, 23, 42, 0.04)"
                      }}
                    >

                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "12px",
                          alignItems: "flex-start"
                        }}
                      >

                        <div>
                          <span
                            style={{
                              display: "inline-block",
                              fontSize: "10px",
                              fontWeight: 800,
                              letterSpacing: "0.08em",
                              color: "#0f766e",
                              marginBottom: "7px"
                            }}
                          >
                            REGULATORY SOURCE
                          </span>

                          <h3 style={{ margin: 0 }}>
                            {document.title}
                          </h3>
                        </div>

                        <span
                          style={{
                            flexShrink: 0,
                            padding: "5px 9px",
                            borderRadius: "999px",
                            background: "#e8f7f5",
                            color: "#0f766e",
                            fontSize: "10px",
                            fontWeight: 700
                          }}
                        >
                          INDEXED
                        </span>

                      </div>

                      <div
                        style={{
                          marginTop: "15px",
                          paddingTop: "13px",
                          borderTop: "1px solid #eef2f6"
                        }}
                      >

                        <p style={{ margin: "0 0 7px", fontSize: "13px" }}>
                          <strong>File:</strong> {document.filename}
                        </p>

                        <p style={{ margin: "0 0 7px", fontSize: "13px" }}>
                          <strong>Type:</strong> {document.document_type}
                        </p>

                        {document.uploaded_at && (
                          <p
                            style={{
                              margin: 0,
                              color: "#64748b",
                              fontSize: "12px"
                            }}
                          >
                            Added:{" "}
                            {new Date(document.uploaded_at).toLocaleString()}
                          </p>
                        )}

                      </div>

                      <div
                        style={{
                          marginTop: "16px",
                          paddingTop: "14px",
                          borderTop: "1px solid #eef2f6",
                          display: "flex",
                          justifyContent: "flex-end"
                        }}
                      >
                        <button
                          type="button"
                          onClick={() =>
                            deleteDocument(document.id, document.filename)
                          }
                          disabled={deletingDocumentId === document.id}
                          style={{
                            padding: "9px 14px",
                            borderRadius: "8px",
                            border: "1px solid #fecaca",
                            background: "#fff7f7",
                            color: "#b91c1c",
                            fontSize: "12px",
                            fontWeight: 700,
                            cursor:
                              deletingDocumentId === document.id
                                ? "not-allowed"
                                : "pointer",
                            opacity:
                              deletingDocumentId === document.id
                                ? 0.6
                                : 1
                          }}
                        >
                          {deletingDocumentId === document.id
                            ? "Deleting..."
                            : "Delete Document"}
                        </button>
                      </div>

                    </div>

                  ))}

                </div>

              )}

            </div>

          </section>

        )}


        {/* =========================
            RECYCLE BIN
        ========================= */}

        {activePage === "bin" && (
          <section>
            <div className="page-header">
              <div>
                <span className="page-label">
                  DOCUMENT RECOVERY
                </span>

                <h2>
                  Recycle Bin
                </h2>

                <p>
                  Deleted documents are kept here so accidental deletion
                  can be safely reversed.
                </p>
              </div>

              <span className="verified-badge">
                {trashDocuments.length} ITEM{trashDocuments.length === 1 ? "" : "S"}
              </span>
            </div>


            {trashDocuments.length === 0 ? (

              <div className="empty-search-state">
                <div className="empty-icon">
                  🗑️
                </div>

                <h3>
                  Recycle bin is empty
                </h3>

                <p>
                  Documents moved from the library will appear here.
                </p>
              </div>

            ) : (

              <div
                style={{
                  display: "grid",
                  gap: "14px",
                  marginTop: "24px"
                }}
              >

                {trashDocuments.map((document) => (

                  <div
                    key={document.id}
                    style={{
                      background: "#ffffff",
                      border: "1px solid #dbe3ec",
                      borderRadius: "14px",
                      padding: "20px",
                      boxShadow: "0 4px 14px rgba(15, 23, 42, 0.04)"
                    }}
                  >

                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: "16px",
                        alignItems: "flex-start",
                        flexWrap: "wrap"
                      }}
                    >

                      <div>
                        <span
                          style={{
                            display: "inline-block",
                            fontSize: "10px",
                            fontWeight: 800,
                            letterSpacing: "0.08em",
                            color: "#b45309",
                            marginBottom: "7px"
                          }}
                        >
                          DELETED DOCUMENT
                        </span>

                        <h3 style={{ margin: 0 }}>
                          {document.title}
                        </h3>
                      </div>

                      <span
                        style={{
                          flexShrink: 0,
                          padding: "5px 9px",
                          borderRadius: "999px",
                          background: "#fff7ed",
                          color: "#b45309",
                          fontSize: "10px",
                          fontWeight: 700
                        }}
                      >
                        IN BIN
                      </span>

                    </div>


                    <div
                      style={{
                        marginTop: "15px",
                        paddingTop: "13px",
                        borderTop: "1px solid #eef2f6"
                      }}
                    >

                      <p style={{ margin: "0 0 7px", fontSize: "13px" }}>
                        <strong>File:</strong> {document.filename}
                      </p>

                      <p style={{ margin: "0 0 7px", fontSize: "13px" }}>
                        <strong>Type:</strong> {document.document_type}
                      </p>

                      <p
                        style={{
                          margin: 0,
                          color: "#64748b",
                          fontSize: "12px"
                        }}
                      >
                        Deleted:{" "}
                        {document.deleted_at
                          ? new Date(document.deleted_at).toLocaleString()
                          : "Unknown"}
                      </p>

                    </div>


                    <div
                      style={{
                        marginTop: "16px",
                        paddingTop: "14px",
                        borderTop: "1px solid #eef2f6",
                        display: "flex",
                        justifyContent: "flex-end",
                        gap: "10px",
                        flexWrap: "wrap"
                      }}
                    >

                      <button
                        type="button"
                        onClick={() =>
                          restoreDocument(document.id, document.filename)
                        }
                        disabled={
                          restoringDocumentId === document.id ||
                          permanentlyDeletingDocumentId === document.id
                        }
                        style={{
                          padding: "9px 14px",
                          borderRadius: "8px",
                          border: "1px solid #99f6e4",
                          background: "#f0fdfa",
                          color: "#0f766e",
                          fontSize: "12px",
                          fontWeight: 700,
                          cursor: "pointer",
                          opacity:
                            restoringDocumentId === document.id
                              ? 0.6
                              : 1
                        }}
                      >
                        {restoringDocumentId === document.id
                          ? "Restoring..."
                          : "Restore Document"}
                      </button>


                      <button
                        type="button"
                        onClick={() =>
                          permanentlyDeleteDocument(
                            document.id,
                            document.filename
                          )
                        }
                        disabled={
                          restoringDocumentId === document.id ||
                          permanentlyDeletingDocumentId === document.id
                        }
                        style={{
                          padding: "9px 14px",
                          borderRadius: "8px",
                          border: "1px solid #fecaca",
                          background: "#fff7f7",
                          color: "#b91c1c",
                          fontSize: "12px",
                          fontWeight: 700,
                          cursor: "pointer",
                          opacity:
                            permanentlyDeletingDocumentId === document.id
                              ? 0.6
                              : 1
                        }}
                      >
                        {permanentlyDeletingDocumentId === document.id
                          ? "Deleting..."
                          : "Delete Forever"}
                      </button>

                    </div>

                  </div>
                ))}

              </div>
            )}

          </section>
        )}


        {/* =========================
            SEARCH
        ========================= */}

        {activePage === "search" && (

          <section>

            <div className="page-header">

              <div>

                <span className="page-label">
                  MINE SAFETY INTELLIGENCE
                </span>

                <h2>
                  Regulatory Search
                </h2>

                <p>
                  Search authoritative MineSafe evidence
                  and supplementary external information.
                </p>

              </div>

            </div>


            {/* SEARCH BOX */}

            <div className="search-page-box">

              <input
                type="text"
                placeholder="Search safety regulations..."
                value={query}
                onChange={(event) =>
                  setQuery(event.target.value)
                }
                onKeyDown={(event) => {

                  if (event.key === "Enter") {
                    searchDocuments();
                  }

                }}
              />

              <button onClick={searchDocuments}>
                Search
              </button>

            </div>


            {/* =========================
                REGULATORY ANSWER
            ========================= */}

            {primaryResult ? (

              <div className="regulatory-answer">

                <div className="answer-header">

                  <div>

                    <span className="result-label">
                      REGULATORY ANSWER
                    </span>

                    <h3>
                      Requirement Identified
                    </h3>

                  </div>

                  <span className="verified-badge">
                    ✓ Evidence Found
                  </span>

                </div>


                <div className="answer-content">

                  <p className="main-evidence">
                   {primaryResult.answer || primaryResult.content}
                  </p>

                </div>


                <div className="answer-source">

                  <div>

                    <span className="source-label">
                      SOURCE
                    </span>

                    <strong>
                      {primaryResult.document_title ||
                        primaryResult.title ||
                        "Regulatory Document"}
                    </strong>

                    <span className="source-file">
                      {primaryResult.filename ||
                        primaryResult.file ||
                        ""}
                    </span>

                  </div>


                  <div className="source-meta">

                    <span>
                      Page {primaryResult.page_number}
                    </span>

                    <span>
                      Chunk {primaryResult.chunk_id}
                    </span>

                    <span>
                      Relevance{" "}
                      {typeof primaryResult.score === "number"
                        ? primaryResult.score.toFixed(3)
                        : "—"}
                    </span>

                  </div>

                </div>


                {/* =========================
                    EXTERNAL INFORMATION
                ========================= */}

                <div className="external-results">

                  <div className="section-heading">

                    <span className="external-label">
                      EXTERNAL INFORMATION
                    </span>

                    <h2>
                      Supplementary Knowledge
                    </h2>

                    <p>
                      Additional context from external
                      sources. It is not used as regulatory
                      compliance evidence.
                    </p>

                  </div>


                  {externalResults.length === 0 ? (

                    <div className="external-empty">

                      <p>
                        No external information found for
                        this query.
                      </p>

                    </div>

                  ) : (

                    externalResults.map(
                      (result, index) => (

                        <div
                          className="external-result-card"
                          key={`${result.title}-${index}`}
                        >

                          <div>

                            <h3>
                              {result.title}
                            </h3>

                            <p>
                              {result.snippet}
                            </p>

                            <span className="external-source">
                              Source: {result.source}
                            </span>

                          </div>


                          <a
                            href={result.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            View Source →
                          </a>

                        </div>

                      )
                    )

                  )}

                </div>


                {/* SUPPORTING EVIDENCE */}

                {supportingResults.length > 0 && (

                  <div className="supporting-section">

                    <button
                      className="supporting-toggle"
                      onClick={() =>
                        setShowSupportingEvidence(
                          !showSupportingEvidence
                        )
                      }
                    >

                      {showSupportingEvidence
                        ? "Hide supporting evidence ↑"
                        : `View ${supportingResults.length} supporting ${supportingResults.length === 1 ? "result" : "results"} ↓`
                      }

                    </button>


                    {showSupportingEvidence && (

                      <div className="supporting-evidence">

                        {supportingResults.map(
                          (result, index) => (

                            <div
                              className="supporting-card"
                              key={`${result.document_id}-${result.chunk_id}-${index}`}
                            >

                              <div className="supporting-card-header">

                                <span>
                                  Supporting Evidence
                                </span>

                                <span>
                                  Relevance{" "}
                                  {typeof result.score === "number"
                                    ? result.score.toFixed(3)
                                    : "—"}
                                </span>

                              </div>


                              <p>
                                {result.content}
                              </p>


                              <div className="supporting-meta">

                                <span>
                                  Page {result.page_number}
                                </span>

                                <span>
                                  Chunk {result.chunk_id}
                                </span>

                              </div>

                            </div>

                          )
                        )}

                      </div>

                    )}

                  </div>

                )}

              </div>

            ) : (

              <div className="empty-search-state">

                <div className="empty-icon">
                  🔎
                </div>

                <h3>
                  Search regulatory evidence
                </h3>

                <p>
                  Enter a safety, engineering or
                  compliance question above.
                </p>

              </div>

            )}

          </section>

        )}

        {/* =========================
            COMPLIANCE
        ========================= */}

        {activePage === "compliance" && (

          <section>

            <h2>
              Compliance Check
            </h2>


            <p>
              Enter the actual airflow measured
              in the mine and compare it against
              the regulatory requirement.
            </p>


            <input
              type="number"
              placeholder="Actual airflow (m3/s)"
              value={actualAirflow}
              onChange={(event) =>
                setActualAirflow(event.target.value)
              }
              onKeyDown={(event) => {

                if (event.key === "Enter") {
                  checkCompliance();
                }

              }}
            />


            <button
              onClick={checkCompliance}
            >
              Check Compliance
            </button>


            {complianceResult && (

              <div className="compliance-result">

                <h3>
                  Result:{" "}
                  {complianceResult.result}
                </h3>


                <p>
                  Severity:{" "}
                  {complianceResult.severity}
                </p>


                <p>
                  {complianceResult.message}
                </p>


                {complianceResult.evidence && (

                  <div className="document">

                    <h3>
                      Regulatory Evidence
                    </h3>


                    <p>
                      Page:{" "}
                      {
                        complianceResult
                          .evidence
                          .page_number
                      }
                    </p>


                    <p>
                      {
                        complianceResult
                          .evidence
                          .text
                      }
                    </p>


                    <p>
                      Required airflow:{" "}
                      {
                        complianceResult
                          .evidence
                          .required_airflow
                      }{" "}
                      m3/s
                    </p>

                  </div>

                )}

              </div>

            )}

          </section>

        )}


        {/* =========================
            INCIDENTS
        ========================= */}

        {activePage === "incidents" && (

          <section>

            <div className="page-header">

              <div>

                <span className="page-label">
                  SAFETY EVENT INTELLIGENCE
                </span>

                <h2>
                  Incident Analysis
                </h2>

                <p>
                  Classify mining safety incidents and
                  prioritize the response.
                </p>

              </div>

            </div>


            <div
              style={{
                background: "#ffffff",
                border: "1px solid #dbe3ec",
                borderRadius: "16px",
                padding: "26px",
                marginTop: "24px",
                boxShadow: "0 6px 20px rgba(15, 23, 42, 0.06)"
              }}
            >

              <label
                style={{
                  display: "block",
                  fontWeight: 700,
                  marginBottom: "10px"
                }}
              >
                Incident Description
              </label>

              <textarea
                placeholder="Example: The main ventilation fan failed and airflow dropped severely."
                value={incidentDescription}
                onChange={(event) =>
                  setIncidentDescription(
                    event.target.value
                  )
                }
                onKeyDown={(event) => {

                  if (
                    (event.ctrlKey || event.metaKey) &&
                    event.key === "Enter"
                  ) {
                    classifyIncident();
                  }

                }}
                style={{
                  width: "100%",
                  minHeight: "140px",
                  resize: "vertical",
                  boxSizing: "border-box",
                  padding: "15px",
                  border: "1px solid #cbd5e1",
                  borderRadius: "10px",
                  fontSize: "14px",
                  lineHeight: "1.6",
                  fontFamily: "inherit"
                }}
              />

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginTop: "14px",
                  gap: "12px",
                  flexWrap: "wrap"
                }}
              >

                <span
                  style={{
                    fontSize: "12px",
                    color: "#64748b"
                  }}
                >
                  Ctrl + Enter to analyze
                </span>

                <button
                  onClick={classifyIncident}
                  disabled={!incidentDescription.trim()}
                  style={{
                    padding: "11px 22px",
                    borderRadius: "9px",
                    border: "none",
                    fontWeight: 700,
                    cursor: incidentDescription.trim()
                      ? "pointer"
                      : "not-allowed",
                    opacity: incidentDescription.trim()
                      ? 1
                      : 0.55
                  }}
                >
                  Analyze Incident
                </button>

              </div>

            </div>


            {incidentResult && (

              <div
                style={{
                  marginTop: "24px",
                  background: "#ffffff",
                  border: "1px solid #dbe3ec",
                  borderRadius: "16px",
                  padding: "26px",
                  boxShadow: "0 6px 20px rgba(15, 23, 42, 0.06)"
                }}
              >

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "16px",
                    flexWrap: "wrap",
                    marginBottom: "22px"
                  }}
                >

                  <div>

                    <span className="result-label">
                      ANALYSIS RESULT
                    </span>

                    <h3
                      style={{
                        marginTop: "8px",
                        marginBottom: "0"
                      }}
                    >
                      Incident Assessment
                    </h3>

                  </div>

                  <span className="verified-badge">
                    ✓ Classified
                  </span>

                </div>


                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fit, minmax(190px, 1fr))",
                    gap: "16px"
                  }}
                >

                  <div
                    style={{
                      padding: "20px",
                      borderRadius: "12px",
                      background: "#f8fafc",
                      border: "1px solid #e2e8f0"
                    }}
                  >

                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        letterSpacing: "0.08em",
                        color: "#64748b"
                      }}
                    >
                      CATEGORY
                    </span>

                    <div
                      style={{
                        fontSize: "22px",
                        fontWeight: 800,
                        marginTop: "8px"
                      }}
                    >
                      {incidentResult.category}
                    </div>

                  </div>


                  <div
                    style={{
                      padding: "20px",
                      borderRadius: "12px",
                      background: "#f8fafc",
                      border: "1px solid #e2e8f0"
                    }}
                  >

                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        letterSpacing: "0.08em",
                        color: "#64748b"
                      }}
                    >
                      PRIORITY
                    </span>

                    <div
                      style={{
                        fontSize: "22px",
                        fontWeight: 800,
                        marginTop: "8px"
                      }}
                    >
                      {incidentResult.priority}
                    </div>

                  </div>

                </div>


                <div
                  style={{
                    marginTop: "18px",
                    padding: "18px",
                    borderRadius: "12px",
                    background: "#f8fafc",
                    border: "1px solid #e2e8f0"
                  }}
                >

                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 700,
                      letterSpacing: "0.08em",
                      color: "#64748b"
                    }}
                  >
                    INCIDENT
                  </span>

                  <p
                    style={{
                      marginBottom: 0,
                      lineHeight: "1.6"
                    }}
                  >
                    {incidentDescription}
                  </p>

                </div>

              </div>

            )}

          </section>

        )}

      </main>

    </div>

  );
}
  
export default App;