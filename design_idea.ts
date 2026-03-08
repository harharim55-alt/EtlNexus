import React, { useState, useEffect, useMemo } from 'react';
import { 
  Database, Search, Sparkles, Network, Layers, 
  Activity, ChevronRight, ArrowRightLeft, 
  Cpu, Lock, FileJson, CheckCircle2, MessageSquare,
  AlertCircle, Server, Copy, Terminal, Check,
  Box, Maximize2, Code
} from 'lucide-react';

// --- MOCK DATA: Dynamic ETL Catalog ---
const MOCK_CATALOG = [
  { 
    id: 'etl-001', name: "Shopify Sales Sync", category: "E-commerce",
    description: "Daily synchronization of e-commerce transactions, orders, and fulfillment statuses.",
    fields: ["order_id", "customer_id", "email", "total_amount", "created_at", "currency", "status"], 
    airflowStatus: "success", schedule: "Daily at 00:00 UTC", rowsPerDay: "50k+",
    sourceTables: ["ecommerce.raw_orders", "ecommerce.raw_customers", "etl.stripe_billing"],
    destinationTables: ["stg_shopify_orders", "stg_shopify_customers"]
  },
  { 
    id: 'etl-002', name: "Zendesk Tickets Stream", category: "Support",
    description: "Real-time streaming of customer support tickets, CSAT scores, and agent interactions.",
    fields: ["ticket_id", "customer_id", "email", "status", "priority", "created_at", "resolution_time_hrs"], 
    airflowStatus: "success", schedule: "Real-time (Streaming)", rowsPerDay: "12k+",
    sourceTables: ["support.tickets_stream", "support.agent_events"],
    destinationTables: ["raw_zendesk_tickets", "raw_csat_scores"]
  },
  { 
    id: 'etl-003', name: "Stripe Billing Aggregator", category: "Finance",
    description: "Aggregates subscription lifecycle events, invoices, and payment failures.",
    fields: ["invoice_id", "customer_id", "amount_due", "status", "payment_date", "subscription_tier"], 
    airflowStatus: "success", schedule: "Hourly", rowsPerDay: "8k+",
    sourceTables: ["etl.mixpanel_events", "finance.invoices", "finance.subscriptions"],
    destinationTables: ["finance_invoices", "finance_subscriptions"]
  },
  { 
    id: 'etl-004', name: "Mixpanel User Events", category: "Analytics",
    description: "Raw user behavior events, feature usage, and session metadata from web and mobile.",
    fields: ["event_id", "user_id", "email", "event_name", "timestamp", "device_type", "country", "session_duration"], 
    airflowStatus: "failed", schedule: "Every 4 Hours", rowsPerDay: "2.5M+",
    sourceTables: ["events.raw_telemetry", "etl.core_backend"],
    destinationTables: ["fact_user_events", "dim_sessions"]
  },
  { 
    id: 'etl-005', name: "Salesforce CRM Sync", category: "Sales",
    description: "Hourly sync of lead pipeline, account details, and opportunity stages.",
    fields: ["account_id", "lead_id", "email", "company_name", "opportunity_stage", "arr_estimate", "owner_id"], 
    airflowStatus: "success", schedule: "Hourly", rowsPerDay: "5k+",
    sourceTables: ["sales.account", "sales.lead", "sales.opportunity"],
    destinationTables: ["crm_accounts", "crm_leads", "crm_opportunities"]
  },
  { 
    id: 'etl-006', name: "PostgreSQL Production DB", category: "Core Backend",
    description: "Nightly snapshot of the core application database.",
    fields: ["user_id", "email", "first_name", "last_name", "signup_date", "is_active", "hashed_password"], 
    airflowStatus: "success", schedule: "Daily at 03:00 UTC", rowsPerDay: "100k+",
    sourceTables: ["public.users", "public.profiles", "public.settings"],
    destinationTables: ["core_users_snapshot", "core_profiles_snapshot"]
  }
];

// --- AI API CONFIG ---
const apiKey = ""; // Environment provides this automatically

export default function App() {
  const [activeTab, setActiveTab] = useState('catalog');
  const [catalog, setCatalog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Default to the first ETL once loaded for the Master-Detail view
  const [selectedEtlId, setSelectedEtlId] = useState(null);

  useEffect(() => {
    const fetchCatalog = async () => {
      setLoading(true);
      await new Promise(resolve => setTimeout(resolve, 600)); // slightly faster mock
      setCatalog(MOCK_CATALOG);
      setSelectedEtlId(MOCK_CATALOG[0].id);
      setLoading(false);
    };
    fetchCatalog();
  }, []);

  const filteredCatalog = useMemo(() => {
    if (!searchQuery) return catalog;
    const lowerQ = searchQuery.toLowerCase();
    return catalog.filter(etl => 
      etl.name.toLowerCase().includes(lowerQ) || 
      etl.description.toLowerCase().includes(lowerQ) ||
      etl.fields.some(f => f.toLowerCase().includes(lowerQ))
    );
  }, [catalog, searchQuery]);

  const selectedEtl = useMemo(() => 
    catalog.find(c => c.id === selectedEtlId) || null
  , [catalog, selectedEtlId]);

  return (
    <div className="flex h-screen bg-[#09090b] text-slate-300 font-sans overflow-hidden selection:bg-indigo-500/30">
      
      {/* Slim Sidebar */}
      <nav className="w-20 border-r border-white/5 bg-[#09090b] flex flex-col items-center py-6 z-20 shrink-0">
        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 p-2.5 rounded-xl shadow-[0_0_20px_rgba(99,102,241,0.3)] mb-8">
          <Layers className="text-white w-6 h-6" />
        </div>

        <div className="flex-1 flex flex-col gap-4 w-full px-3">
          <NavIcon active={activeTab === 'catalog'} onClick={() => setActiveTab('catalog')} icon={<Database className="w-5 h-5"/>} tooltip="ETL Catalog" />
          <NavIcon active={activeTab === 'matrix'} onClick={() => setActiveTab('matrix')} icon={<Network className="w-5 h-5"/>} tooltip="Field Matrix" />
          <NavIcon active={activeTab === 'ai'} onClick={() => setActiveTab('ai')} icon={<Sparkles className="w-5 h-5"/>} tooltip="AI Architect" />
        </div>

        <div className="mt-auto group relative cursor-pointer">
          <Activity className="w-5 h-5 text-emerald-400" />
          <div className="absolute left-full ml-4 top-1/2 -translate-y-1/2 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap transition-opacity">
            Airflow: Online
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0">
        
        {loading ? (
          <LoadingState />
        ) : (
          <div className="flex h-full">
            {activeTab === 'catalog' && (
              <>
                {/* MASTER VIEW (List) */}
                <div className="w-[400px] border-r border-white/5 flex flex-col bg-[#09090b] shrink-0">
                  <div className="p-6 border-b border-white/5">
                    <h2 className="text-xl font-medium text-white tracking-tight mb-4">Pipeline Registry</h2>
                    <div className="relative">
                      <Search className="h-4 w-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        placeholder="Search pipelines or fields..."
                        className="w-full bg-[#18181b] border border-white/10 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="flex-1 overflow-y-auto p-3 space-y-1 custom-scrollbar">
                    {filteredCatalog.map(etl => (
                      <EtlListItem 
                        key={etl.id} 
                        etl={etl} 
                        isActive={selectedEtlId === etl.id}
                        onClick={() => setSelectedEtlId(etl.id)}
                      />
                    ))}
                  </div>
                </div>

                {/* DETAIL VIEW (Bento Box Workspace) */}
                <div className="flex-1 overflow-y-auto bg-[#09090b] relative">
                  {selectedEtl ? (
                    <BentoWorkspace etl={selectedEtl} catalog={catalog} />
                  ) : (
                    <div className="flex h-full items-center justify-center text-slate-500">
                      Select a pipeline to view details
                    </div>
                  )}
                </div>
              </>
            )}

            {activeTab === 'matrix' && (
              <div className="flex-1 overflow-y-auto p-8 bg-[#09090b]">
                <FieldMatrixView catalog={catalog} />
              </div>
            )}
            
            {activeTab === 'ai' && (
              <div className="flex-1 flex items-center justify-center p-8 bg-[#09090b]">
                <AIArchitectView catalog={catalog} />
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

// --- NAVIGATION COMPONENT ---
function NavIcon({ active, onClick, icon, tooltip }) {
  return (
    <div className="relative group flex justify-center">
      <button
        onClick={onClick}
        className={`p-3 rounded-xl transition-all duration-200 ${
          active 
            ? 'bg-indigo-500/10 text-indigo-400 shadow-[inset_0_0_0_1px_rgba(99,102,241,0.2)]' 
            : 'text-slate-500 hover:bg-white/5 hover:text-slate-300'
        }`}
      >
        {icon}
      </button>
      <div className="absolute left-full ml-4 top-1/2 -translate-y-1/2 bg-[#18181b] border border-white/10 text-white text-xs font-medium px-2.5 py-1.5 rounded-md opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap transition-opacity shadow-xl z-50">
        {tooltip}
      </div>
    </div>
  );
}

// --- MASTER LIST ITEM ---
function EtlListItem({ etl, isActive, onClick }) {
  const isSuccess = etl.airflowStatus === 'success';
  return (
    <div 
      onClick={onClick}
      className={`p-4 rounded-xl cursor-pointer transition-all duration-200 border ${
        isActive 
          ? 'bg-[#18181b] border-indigo-500/30 shadow-[0_4px_20px_rgba(0,0,0,0.2)]' 
          : 'bg-transparent border-transparent hover:bg-white/5'
      }`}
    >
      <div className="flex items-start justify-between mb-1">
        <h3 className={`font-medium text-sm truncate pr-4 ${isActive ? 'text-indigo-400' : 'text-slate-200'}`}>
          {etl.name}
        </h3>
        <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${isSuccess ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)] animate-pulse'}`} />
      </div>
      <div className="text-xs text-slate-500 font-mono mb-3">{etl.category}</div>
      <div className="flex gap-2 text-[10px] font-mono">
        <span className="px-2 py-0.5 rounded bg-white/5 text-slate-400 border border-white/5">{etl.schedule}</span>
        <span className="px-2 py-0.5 rounded bg-white/5 text-slate-400 border border-white/5">{etl.rowsPerDay}</span>
      </div>
    </div>
  );
}

// --- DETAIL VIEW: BENTO WORKSPACE ---
function BentoWorkspace({ etl, catalog }) {
  const isSuccess = etl.airflowStatus === 'success';
  const [copied, setCopied] = useState(false);

  const getMockDataType = (fieldName) => {
    const lower = fieldName.toLowerCase();
    if (lower.includes('id')) return 'UUID';
    if (lower.includes('amount') || lower.includes('price')) return 'FLOAT8';
    if (lower.includes('date') || lower.includes('time') || lower.includes('created')) return 'TIMESTAMP';
    if (lower.includes('is_') || lower.includes('has_')) return 'BOOL';
    return 'VARCHAR';
  };

  const importName = etl.name.toLowerCase().replace(/ /g, '_');

  const handleCopyCode = () => {
    const code = `from etls import ${importName}\n\n${importName}("2026-01-25").consume()`;
    const textArea = document.createElement("textarea");
    textArea.value = code;
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand('copy');
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {}
    document.body.removeChild(textArea);
  };

  const relatedEtls = catalog.filter(c => 
    c.id !== etl.id && c.fields.some(f => etl.fields.includes(f))
  ).map(c => ({
    ...c,
    sharedFields: c.fields.filter(f => etl.fields.includes(f))
  }));

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-6">
      
      {/* Bento Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-[10px] font-mono uppercase tracking-widest text-indigo-400 bg-indigo-500/10 px-2 py-1 rounded border border-indigo-500/20">
              {etl.category}
            </span>
            <span className={`text-[10px] font-mono uppercase tracking-widest px-2 py-1 rounded border ${
              isSuccess ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' : 'text-rose-400 bg-rose-500/10 border-rose-500/20'
            }`}>
              {isSuccess ? 'Airflow: Success' : 'Airflow: Failed'}
            </span>
          </div>
          <h1 className="text-3xl font-semibold text-white tracking-tight">{etl.name}</h1>
          <p className="text-slate-400 mt-2 max-w-2xl text-sm leading-relaxed">{etl.description}</p>
        </div>
      </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-12 gap-6">
        
        {/* Box 1: Lineage */}
        <div className="col-span-12 lg:col-span-8 bg-[#18181b] border border-white/5 rounded-2xl p-6 relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-6 flex items-center gap-2">
            <Network className="w-3.5 h-3.5" /> Pipeline Topology
          </h3>
          <div className="flex items-start justify-between w-full max-w-3xl mx-auto mt-4">
            
            {/* Source Upstreams */}
            <div className="flex flex-col items-center gap-3 w-40">
              <div className="w-12 h-12 bg-white/5 border border-white/10 rounded-xl flex items-center justify-center shadow-lg">
                <Database className="w-5 h-5 text-slate-300"/>
              </div>
              <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500 text-center">Reads From</span>
              <div className="flex flex-col gap-1.5 w-full mt-1">
                {etl.sourceTables?.map(t => (
                  <span key={t} className="text-[10px] bg-[#09090b] px-2 py-1.5 rounded text-slate-400 font-mono border border-white/5 truncate text-center" title={t}>
                    {t}
                  </span>
                ))}
              </div>
            </div>
            
            {/* Pipeline Flow */}
            <div className="flex-1 px-4 relative flex items-center justify-center h-12">
              <div className={`h-[1px] w-full ${isSuccess ? 'bg-emerald-500/30' : 'bg-rose-500/30'} relative flex items-center justify-center`}>
                <div className={`absolute w-3 h-3 rounded-full ${isSuccess ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.8)]' : 'bg-rose-400 shadow-[0_0_10px_rgba(251,113,133,0.8)]'} z-10 animate-[pulse_2s_ease-in-out_infinite]`}></div>
              </div>
            </div>

            {/* Destination */}
            <div className="flex flex-col items-center gap-3 w-40">
              <div className="w-12 h-12 bg-indigo-500/10 border border-indigo-500/30 rounded-xl flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.15)]">
                <Layers className="w-5 h-5 text-indigo-400"/>
              </div>
              <span className="text-[10px] font-mono uppercase tracking-widest text-indigo-400/80 text-center">Writes To</span>
              <div className="flex flex-col gap-1.5 w-full mt-1">
                {etl.destinationTables?.map(t => (
                  <span key={t} className="text-[10px] bg-indigo-500/5 px-2 py-1.5 rounded text-indigo-300/80 font-mono border border-indigo-500/20 truncate text-center" title={t}>
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Box 2: Metrics */}
        <div className="col-span-12 lg:col-span-4 grid grid-rows-2 gap-6">
          <div className="bg-[#18181b] border border-white/5 rounded-2xl p-5 flex flex-col justify-center">
             <div className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-1">Volume Rate</div>
             <div className="flex items-end gap-2">
               <span className="text-2xl font-semibold text-white tracking-tight">{etl.rowsPerDay}</span>
               <span className="text-sm text-slate-500 mb-1">rows/day</span>
             </div>
          </div>
          <div className="bg-[#18181b] border border-white/5 rounded-2xl p-5 flex flex-col justify-center">
             <div className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-1">Schedule</div>
             <div className="text-lg font-medium text-white">{etl.schedule}</div>
          </div>
        </div>

        {/* Box 3: Schema */}
        <div className="col-span-12 lg:col-span-7 bg-[#18181b] border border-white/5 rounded-2xl flex flex-col overflow-hidden max-h-[460px]">
          <div className="p-5 border-b border-white/5 bg-[#18181b]/50 backdrop-blur">
            <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
              <Box className="w-3.5 h-3.5" /> Data Structure
            </h3>
          </div>
          <div className="overflow-y-auto p-2 custom-scrollbar">
            {etl.fields.map((field, idx) => (
              <div key={field} className="flex justify-between items-center px-4 py-2.5 rounded-lg hover:bg-white/5 transition-colors group">
                <div className="flex items-center gap-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-700 group-hover:bg-indigo-500 transition-colors"></div>
                  <span className="font-mono text-sm text-slate-300 group-hover:text-white transition-colors">{field}</span>
                </div>
                <span className="text-[10px] text-slate-500 font-mono bg-[#09090b] px-2 py-1 rounded border border-white/5">
                  {getMockDataType(field)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Box 4 & 5 Stack */}
        <div className="col-span-12 lg:col-span-5 flex flex-col gap-6">
          
          {/* Quick Consume Snippet */}
          <div className="bg-[#18181b] border border-white/5 rounded-2xl p-5 shrink-0">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
                <Code className="w-3.5 h-3.5" /> Import & Consume
              </h3>
              <button 
                onClick={handleCopyCode}
                className="text-xs font-medium flex items-center gap-1.5 text-indigo-400 hover:text-indigo-300 transition-colors bg-indigo-500/10 px-2.5 py-1 rounded border border-indigo-500/20"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
            <div className="bg-[#09090b] rounded-xl p-4 border border-white/5 overflow-x-auto">
              <code className="text-xs font-mono leading-relaxed text-slate-300">
                <span className="text-pink-500">from</span> etls <span className="text-pink-500">import</span> {importName}<br/><br/>
                <span className="text-indigo-400">{importName}</span>(<span className="text-amber-400">"2026-01-25"</span>).consume()
              </code>
            </div>
          </div>

          {/* Join Suggestions */}
          <div className="bg-[#18181b] border border-white/5 rounded-2xl p-5 flex-1 flex flex-col gap-5">
            
            {/* Simple Field Matches */}
            {relatedEtls.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-400 flex items-center gap-2">
                    <Database className="w-3.5 h-3.5" /> Schema Matches
                  </h3>
                </div>
                <div className="space-y-2">
                  {relatedEtls.slice(0, 2).map(rel => (
                    <div key={rel.id} className="p-2.5 rounded-lg bg-white/5 border border-white/5 flex flex-col gap-1.5">
                      <div className="font-medium text-[13px] text-slate-200">{rel.name}</div>
                      <div className="flex flex-wrap gap-1.5 items-center">
                        <span className="text-[10px] text-slate-500 font-mono">ON:</span>
                        {rel.sharedFields.map(f => (
                          <span key={f} className="text-[10px] bg-[#09090b] text-slate-300 px-1.5 py-0.5 rounded font-mono border border-white/10">
                            {f}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* AI Insights */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <h3 className="text-[11px] font-mono uppercase tracking-widest text-indigo-300 flex items-center gap-2">
                  <Sparkles className="w-3.5 h-3.5" /> AI Insight
                </h3>
              </div>
              <div className="p-3.5 rounded-lg bg-indigo-500/5 border border-indigo-500/10 text-xs text-indigo-200/80 leading-relaxed">
                Semantically, <span className="text-indigo-300 font-mono">email</span> in this pipeline uniquely maps to customer profiles in <span className="text-white font-medium">PostgreSQL Production DB</span>. Joining these enables unified historical analysis without relying solely on IDs.
              </div>
            </div>

          </div>

        </div>
      </div>
    </div>
  );
}

// --- FIELD MATRIX VIEW ---
function FieldMatrixView({ catalog }) {
  const fieldMap = useMemo(() => {
    const map = {};
    catalog.forEach(etl => {
      etl.fields.forEach(field => {
        if (!map[field]) map[field] = [];
        map[field].push(etl);
      });
    });
    return Object.entries(map).sort((a, b) => b[1].length - a[1].length);
  }, [catalog]);

  const commonFields = fieldMap.filter(([_, etls]) => etls.length > 1);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-semibold text-white tracking-tight">Global Schema Matrix</h2>
          <p className="text-sm text-slate-400 mt-1">Discover cross-product join keys automatically identified across all pipelines.</p>
        </div>
      </div>

      <div className="bg-[#18181b] border border-white/5 rounded-2xl overflow-hidden shadow-2xl">
        <div className="grid grid-cols-12 gap-4 p-5 border-b border-white/5 bg-[#18181b] text-[11px] font-mono uppercase tracking-widest text-slate-500">
          <div className="col-span-3">Entity Key</div>
          <div className="col-span-1 text-center">Freq</div>
          <div className="col-span-8">Present in Data Models</div>
        </div>
        
        <div className="divide-y divide-white/5">
          {commonFields.map(([field, etls]) => (
            <div key={field} className="grid grid-cols-12 gap-4 p-5 items-center hover:bg-white/5 transition-colors group">
              <div className="col-span-3">
                <span className="font-mono text-xs font-medium text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20 group-hover:bg-emerald-500/20 transition-colors">
                  {field}
                </span>
              </div>
              <div className="col-span-1 text-center text-slate-300 font-mono text-sm">
                {etls.length}
              </div>
              <div className="col-span-8 flex flex-wrap gap-2 items-center">
                {etls.map((etl, idx) => (
                  <React.Fragment key={etl.id}>
                    <div className="flex items-center gap-1.5 bg-[#09090b] px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 border border-white/5">
                      <Database className="w-3 h-3 text-slate-600" />
                      {etl.name}
                    </div>
                    {idx < etls.length - 1 && <ArrowRightLeft className="w-3 h-3 text-slate-700" />}
                  </React.Fragment>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// --- AI ARCHITECT VIEW ---
function AIArchitectView({ catalog }) {
  const [prompt, setPrompt] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { role: 'assistant', content: "SYSTEM INITIALIZED. I am your automated Data Architect. State your metric objective, and I will output the required pipeline joins and transformations." }
  ]);
  const [isTyping, setIsTyping] = useState(false);

  const handleSend = async () => {
    if (!prompt.trim()) return;
    
    const userMsg = prompt;
    setPrompt('');
    setChatHistory(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsTyping(true);

    try {
      const systemPrompt = `You are an expert Data Architect. The user wants to achieve a data goal.
      Here is our current JSON catalog of available ETL pipelines: ${JSON.stringify(catalog)}.
      Analyze their request and suggest:
      1. Which specific ETLs they should use.
      2. Exactly which fields to join on.
      Format your response in clean, easy-to-read markdown. Keep it under 150 words.`;

      const payload = {
        contents: [{ parts: [{ text: userMsg }] }],
        systemInstruction: { parts: [{ text: systemPrompt }] }
      };

      const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${apiKey}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      let aiText = "Query failed.";
      if (data.candidates && data.candidates[0].content.parts[0].text) {
        aiText = data.candidates[0].content.parts[0].text;
      } else if (data.error) {
         aiText = `*API Error:* Please ensure the Gemini API key is configured correctly.`;
      }

      setChatHistory(prev => [...prev, { role: 'assistant', content: aiText }]);
    } catch (error) {
      setChatHistory(prev => [...prev, { role: 'assistant', content: "Connection to Architect Core severed." }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="w-full max-w-4xl h-full max-h-[800px] flex flex-col bg-[#18181b] border border-white/5 rounded-2xl overflow-hidden shadow-2xl relative">
      
      {/* Terminal Header */}
      <div className="bg-[#09090b] p-4 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-rose-500/20 border border-rose-500/50"></div>
            <div className="w-3 h-3 rounded-full bg-amber-500/20 border border-amber-500/50"></div>
            <div className="w-3 h-3 rounded-full bg-emerald-500/20 border border-emerald-500/50"></div>
          </div>
          <div className="text-xs font-mono text-slate-500 ml-2 border-l border-white/10 pl-3">Architect_Terminal_v2.0</div>
        </div>
        <Cpu className="w-4 h-4 text-indigo-500/50" />
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
        {chatHistory.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] p-4 rounded-xl text-sm font-mono leading-relaxed ${
              msg.role === 'user' 
                ? 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/20' 
                : 'bg-[#09090b] text-slate-300 border border-white/5'
            }`}>
              <div className="whitespace-pre-wrap">
                {msg.content.split('**').map((part, i) => 
                  i % 2 === 1 ? <span key={i} className="text-white font-semibold">{part}</span> : part
                )}
              </div>
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-[#09090b] border border-white/5 p-4 rounded-xl flex gap-1.5 items-center">
              <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-pulse"></div>
              <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-pulse delay-75"></div>
              <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-pulse delay-150"></div>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 bg-[#09090b] border-t border-white/5">
        <div className="relative flex items-center bg-[#18181b] border border-white/10 rounded-lg p-1">
          <span className="text-indigo-500 font-mono ml-3 mr-2">&gt;</span>
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Input analytical objective..."
            className="w-full bg-transparent py-2.5 px-2 text-sm font-mono text-slate-300 placeholder-slate-600 focus:outline-none"
          />
          <button 
            onClick={handleSend}
            disabled={isTyping || !prompt.trim()}
            className="p-2 bg-indigo-500/20 hover:bg-indigo-500/40 disabled:bg-transparent text-indigo-400 rounded transition-colors mr-1"
          >
            <MessageSquare className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center h-full bg-[#09090b] text-slate-500 gap-4">
      <div className="flex items-center gap-1">
        <div className="w-2 h-8 bg-indigo-500/50 rounded animate-pulse"></div>
        <div className="w-2 h-12 bg-indigo-500/80 rounded animate-pulse delay-75"></div>
        <div className="w-2 h-6 bg-indigo-500/30 rounded animate-pulse delay-150"></div>
      </div>
      <p className="font-mono text-xs tracking-widest uppercase">Initializing Registry...</p>
    </div>
  );
}