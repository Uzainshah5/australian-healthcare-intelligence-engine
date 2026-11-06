import React, { useState, useMemo, useEffect } from 'react';
import './App.css';
import rawPracticesData from './data/practices.json';
import {
  Building2,
  Search,
  Download,
  Phone,
  Globe,
  MapPin,
  Clock,
  Sparkles,
  CheckCircle2,
  Copy,
  ExternalLink,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  X,
  Layers,
  ArrowUpDown,
  PlusCircle,
  Loader2,
  AlertCircle
} from 'lucide-react';

export interface PracticeRecord {
  practice_id: string;
  practice_name: string;
  practice_address: string;
  suburb: string;
  state: string;
  postcode: string;
  phone_main: string;
  phone_verified?: boolean | number;
  phone_type?: string;
  phone_verification_notes?: string;
  website_url?: string;
  billing_model: string;
  billing_model_evidence?: string;
  telehealth_available: boolean | number;
  wheelchair_accessible: boolean | number;
  opening_hours_summary?: string;
  booking_platform: string;
  opportunity_score: number;
  growth_outreach_hook?: string;
  source_url: string;
  collected_at_utc: string;
  ai_confidence_score: number;
  validation_status: string;
}

export const App: React.FC = () => {
  const [practices, setPractices] = useState<PracticeRecord[]>(rawPracticesData as PracticeRecord[]);
  const [isScraping, setIsScraping] = useState<boolean>(false);
  const [scrapeFeedback, setScrapeFeedback] = useState<{ type: 'success' | 'error' | 'info'; message: string; addedCount?: number } | null>(null);

  // Fetch latest practices from backend API if available
  useEffect(() => {
    fetch('/api/practices')
      .then(res => {
        if (!res.ok) throw new Error('API server offline');
        return res.json();
      })
      .then((data: PracticeRecord[]) => {
        if (Array.isArray(data) && data.length > 0) {
          setPractices(data);
        }
      })
      .catch(() => {
        // Fall back gracefully to bundled practices.json
      });
  }, []);

  const handleAddMoreRecords = async (batchCount: number = 5) => {
    if (isScraping) return;
    setIsScraping(true);
    setScrapeFeedback({
      type: 'info',
      message: `Triggering live scraping & AI verification engine for ${batchCount} new Australian clinics...`
    });

    try {
      const response = await fetch('/api/scrape-more', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: batchCount })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Scraper server error' }));
        throw new Error(errorData.detail || `Server responded with ${response.status}`);
      }

      const result = await response.json();
      if (Array.isArray(result.practices) && result.practices.length > 0) {
        setPractices(result.practices);
      }
      setScrapeFeedback({
        type: 'success',
        message: result.message || `Successfully scraped & enriched ${result.added_count} new Australian medical practices!`,
        addedCount: result.added_count
      });

      // Auto-clear feedback after 6 seconds
      setTimeout(() => {
        setScrapeFeedback(null);
      }, 6000);
    } catch (err: any) {
      setScrapeFeedback({
        type: 'error',
        message: `Failed to scrape more records: ${err?.message || 'Check if python server.py is running'}`
      });
    } finally {
      setIsScraping(false);
    }
  };

  // Filter & Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedState, setSelectedState] = useState<string>('ALL');
  const [selectedBilling, setSelectedBilling] = useState<string>('ALL');
  const [selectedPlatform, setSelectedPlatform] = useState<string>('ALL');
  const [minScore, setMinScore] = useState<number>(0);
  const [telehealthOnly, setTelehealthOnly] = useState<boolean>(false);
  const [wheelchairOnly, setWheelchairOnly] = useState<boolean>(false);

  // Sorting & Pagination State
  const [sortBy, setSortBy] = useState<'name' | 'score' | 'state' | 'billing'>('score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [itemsPerPage, setItemsPerPage] = useState<number>(15);

  // Modal State
  const [selectedPractice, setSelectedPractice] = useState<PracticeRecord | null>(null);
  const [showArchitectureModal, setShowArchitectureModal] = useState<boolean>(false);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  // Top Global KPIs
  const globalKpis = useMemo(() => {
    const total = practices.length;
    const highFit = practices.filter(p => p.opportunity_score >= 80).length;
    const bulkBilling = practices.filter(p => p.billing_model === 'bulk_billing').length;
    const modernBooking = practices.filter(p => ['hotdoc', 'healthengine'].includes(p.booking_platform.toLowerCase())).length;
    const avgScore = (practices.reduce((sum, p) => sum + p.opportunity_score, 0) / (total || 1)).toFixed(1);

    return {
      total,
      highFit,
      highFitPct: Math.round((highFit / total) * 100),
      bulkBillingPct: Math.round((bulkBilling / total) * 100),
      modernBookingPct: Math.round((modernBooking / total) * 100),
      avgScore
    };
  }, [practices]);

  // Analytics Distributions
  const analytics = useMemo(() => {
    const states: Record<string, number> = {};
    const billing: Record<string, number> = {
      mixed_billing: 0,
      bulk_billing: 0,
      private_billing: 0,
      unknown: 0
    };
    const platforms: Record<string, number> = {};

    practices.forEach(p => {
      states[p.state] = (states[p.state] || 0) + 1;
      const bKey = p.billing_model.toLowerCase();
      if (bKey in billing) billing[bKey]++;
      else billing.unknown++;
      platforms[p.booking_platform] = (platforms[p.booking_platform] || 0) + 1;
    });

    return { states, billing, platforms };
  }, [practices]);

  // Filtered & Sorted Records
  const filteredPractices = useMemo(() => {
    return practices
      .filter(p => {
        // Search query matching
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchName = p.practice_name.toLowerCase().includes(q);
          const matchSuburb = p.suburb.toLowerCase().includes(q);
          const matchAddress = p.practice_address.toLowerCase().includes(q);
          const matchPostcode = p.postcode.includes(q);
          if (!matchName && !matchSuburb && !matchAddress && !matchPostcode) return false;
        }

        // State filter
        if (selectedState !== 'ALL' && p.state !== selectedState) return false;

        // Billing filter
        if (selectedBilling !== 'ALL' && p.billing_model.toLowerCase() !== selectedBilling.toLowerCase()) return false;

        // Platform filter
        if (selectedPlatform !== 'ALL' && p.booking_platform.toLowerCase() !== selectedPlatform.toLowerCase()) return false;

        // Opportunity Score threshold
        if (p.opportunity_score < minScore) return false;

        // Telehealth toggle
        if (telehealthOnly && !Boolean(p.telehealth_available)) return false;

        // Wheelchair toggle
        if (wheelchairOnly && !Boolean(p.wheelchair_accessible)) return false;

        return true;
      })
      .sort((a, b) => {
        let valA = a[sortBy === 'name' ? 'practice_name' : sortBy === 'score' ? 'opportunity_score' : sortBy === 'state' ? 'state' : 'billing_model'];
        let valB = b[sortBy === 'name' ? 'practice_name' : sortBy === 'score' ? 'opportunity_score' : sortBy === 'state' ? 'state' : 'billing_model'];

        if (typeof valA === 'string') {
          return sortOrder === 'asc' ? (valA as string).localeCompare(valB as string) : (valB as string).localeCompare(valA as string);
        } else {
          return sortOrder === 'asc' ? (valA as number) - (valB as number) : (valB as number) - (valA as number);
        }
      });
  }, [practices, searchQuery, selectedState, selectedBilling, selectedPlatform, minScore, telehealthOnly, wheelchairOnly, sortBy, sortOrder]);

  // Pagination Slice
  const totalPages = Math.ceil(filteredPractices.length / itemsPerPage) || 1;
  const paginatedPractices = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredPractices.slice(start, start + itemsPerPage);
  }, [filteredPractices, currentPage, itemsPerPage]);

  const handleSort = (field: 'name' | 'score' | 'state' | 'billing') => {
    if (sortBy === field) {
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortOrder(field === 'score' ? 'desc' : 'asc');
    }
  };

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopyFeedback(label);
    setTimeout(() => setCopyFeedback(null), 2500);
  };

  const resetFilters = () => {
    setSearchQuery('');
    setSelectedState('ALL');
    setSelectedBilling('ALL');
    setSelectedPlatform('ALL');
    setMinScore(0);
    setTelehealthOnly(false);
    setWheelchairOnly(false);
    setCurrentPage(1);
  };

  const exportFilteredCSV = () => {
    const headers = [
      'practice_id', 'practice_name', 'practice_address', 'suburb', 'state', 'postcode',
      'phone_main', 'website_url', 'billing_model', 'telehealth_available',
      'wheelchair_accessible', 'booking_platform', 'opportunity_score', 'growth_outreach_hook'
    ];
    const rows = filteredPractices.map(p => [
      `"${p.practice_id}"`,
      `"${p.practice_name.replace(/"/g, '""')}"`,
      `"${p.practice_address.replace(/"/g, '""')}"`,
      `"${p.suburb}"`,
      `"${p.state}"`,
      `"${p.postcode}"`,
      `"${p.phone_main}"`,
      `"${p.website_url || ''}"`,
      `"${p.billing_model}"`,
      p.telehealth_available ? 1 : 0,
      p.wheelchair_accessible ? 1 : 0,
      `"${p.booking_platform}"`,
      p.opportunity_score,
      `"${(p.growth_outreach_hook || '').replace(/"/g, '""')}"`
    ]);

    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `australian_gps_filtered_${filteredPractices.length}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportFilteredJSON = () => {
    const jsonStr = JSON.stringify(filteredPractices, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `australian_gps_filtered_${filteredPractices.length}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="app-container">
      {/* 1. Header Section */}
      <header className="dashboard-header">
        <div className="brand-section">
          <div className="brand-icon-box">
            <Building2 size={26} />
          </div>
          <div>
            <h1 className="brand-title">Australian GP Healthcare Intelligence Hub</h1>
            <p className="brand-subtitle">
              <span>AI Growth & Automation Data Engineering Platform</span>
              <span>•</span>
              <span className="telemetry-pill">
                <span className="pulse-dot"></span>
                {practices.length} Validated Clinics Active
              </span>
            </p>
          </div>
        </div>

        <div className="header-actions">
          <button
            id="add-more-records-btn"
            onClick={() => handleAddMoreRecords(5)}
            className="btn btn-scrape-add"
            disabled={isScraping}
            title="Scrape and AI-enrich new Australian GP records dynamically from the web"
          >
            {isScraping ? (
              <>
                <Loader2 size={16} className="spin-animation" />
                <span>Scraping Net...</span>
              </>
            ) : (
              <>
                <PlusCircle size={16} />
                <span>Add More Records</span>
              </>
            )}
          </button>

          <button
            onClick={() => setShowArchitectureModal(true)}
            className="btn btn-secondary"
            title="View Pipeline Architecture & Statutory Compliance"
          >
            <ShieldCheck size={16} />
            <span>Architecture & Privacy</span>
          </button>

          <button onClick={exportFilteredCSV} className="btn btn-outline-cyan">
            <Download size={15} />
            <span>Export CSV ({filteredPractices.length})</span>
          </button>

          <button onClick={exportFilteredJSON} className="btn btn-primary">
            <Download size={15} />
            <span>Export JSON</span>
          </button>
        </div>
      </header>

      {/* Dynamic Scrape Feedback Banner */}
      {scrapeFeedback && (
        <div className={`scrape-banner ${scrapeFeedback.type}`}>
          <div className="scrape-banner-content">
            {scrapeFeedback.type === 'info' && <Loader2 size={18} className="spin-animation banner-icon" />}
            {scrapeFeedback.type === 'success' && <CheckCircle2 size={18} className="banner-icon" />}
            {scrapeFeedback.type === 'error' && <AlertCircle size={18} className="banner-icon" />}
            <span>{scrapeFeedback.message}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {scrapeFeedback.addedCount !== undefined && scrapeFeedback.addedCount > 0 && (
              <span className="badge-new-records">+{scrapeFeedback.addedCount} Added</span>
            )}
            <button
              onClick={() => setScrapeFeedback(null)}
              className="banner-close-btn"
              title="Dismiss notification"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      {/* 2. Top KPI Stat Cards */}
      <section className="kpi-grid">
        <div className="glass-panel kpi-card" style={{ '--card-accent': '#6366f1' } as React.CSSProperties}>
          <div className="kpi-header">
            <span className="kpi-title">Total Validated Clinics</span>
            <div className="kpi-icon-wrap">
              <Building2 size={16} />
            </div>
          </div>
          <div className="kpi-value">{globalKpis.total}</div>
          <div className="kpi-subtext">Across 7 States & Territories</div>
        </div>

        <div className="glass-panel kpi-card" style={{ '--card-accent': '#10b981' } as React.CSSProperties}>
          <div className="kpi-header">
            <span className="kpi-title">High Opportunity Leads</span>
            <div className="kpi-icon-wrap">
              <Sparkles size={16} />
            </div>
          </div>
          <div className="kpi-value">{globalKpis.highFit}</div>
          <div className="kpi-subtext">{globalKpis.highFitPct}% score ≥ 80 (Prime B2B Targets)</div>
        </div>

        <div className="glass-panel kpi-card" style={{ '--card-accent': '#06b6d4' } as React.CSSProperties}>
          <div className="kpi-header">
            <span className="kpi-title">Bulk-Billing Adoption</span>
            <div className="kpi-icon-wrap">
              <CheckCircle2 size={16} />
            </div>
          </div>
          <div className="kpi-value">{globalKpis.bulkBillingPct}%</div>
          <div className="kpi-subtext">{analytics.billing.bulk_billing} practices fully bulk-billed</div>
        </div>

        <div className="glass-panel kpi-card" style={{ '--card-accent': '#f59e0b' } as React.CSSProperties}>
          <div className="kpi-header">
            <span className="kpi-title">Modern Online Booking</span>
            <div className="kpi-icon-wrap">
              <Globe size={16} />
            </div>
          </div>
          <div className="kpi-value">{globalKpis.modernBookingPct}%</div>
          <div className="kpi-subtext">Using HotDoc or Healthengine integrations</div>
        </div>

        <div className="glass-panel kpi-card" style={{ '--card-accent': '#ec4899' } as React.CSSProperties}>
          <div className="kpi-header">
            <span className="kpi-title">Avg Opportunity Fit</span>
            <div className="kpi-icon-wrap">
              <TrendingUp size={16} />
            </div>
          </div>
          <div className="kpi-value">{globalKpis.avgScore}<span style={{ fontSize: '1rem', color: 'var(--text-muted)' }}>/100</span></div>
          <div className="kpi-subtext">Automated algorithmic scoring index</div>
        </div>
      </section>

      {/* 3. Visual Analytics Section */}
      <section className="analytics-row">
        {/* State Breakdown Bar Chart */}
        <div className="glass-panel chart-card">
          <div className="chart-card-title">
            <MapPin size={16} color="#6366f1" />
            <span>Geographic Distribution Across Australia</span>
          </div>
          <div className="state-bars-container">
            {Object.entries(analytics.states)
              .sort((a, b) => b[1] - a[1])
              .map(([st, count]) => {
                const maxStateCount = Math.max(...Object.values(analytics.states));
                const pct = Math.round((count / maxStateCount) * 100);
                return (
                  <div key={st} className="state-bar-row">
                    <span className="state-tag">{st}</span>
                    <div className="bar-track">
                      <div className="bar-fill" style={{ width: `${pct}%` }}></div>
                    </div>
                    <span className="state-count-label">{count} practices</span>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Billing Model Breakdown */}
        <div className="glass-panel chart-card">
          <div className="chart-card-title">
            <Layers size={16} color="#06b6d4" />
            <span>Medicare Billing Structure</span>
          </div>
          <div className="breakdown-list">
            <div className="breakdown-item">
              <div className="breakdown-meta">
                <span style={{ color: '#a5b4fc' }}>Mixed Billing (Private Gap + Bulk)</span>
                <span>{analytics.billing.mixed_billing} ({Math.round((analytics.billing.mixed_billing / practices.length) * 100)}%)</span>
              </div>
              <div className="breakdown-bar-track">
                <div style={{ height: '100%', width: `${(analytics.billing.mixed_billing / practices.length) * 100}%`, background: '#6366f1', borderRadius: '9999px' }}></div>
              </div>
            </div>

            <div className="breakdown-item">
              <div className="breakdown-meta">
                <span style={{ color: '#34d399' }}>100% Bulk Billing</span>
                <span>{analytics.billing.bulk_billing} ({Math.round((analytics.billing.bulk_billing / practices.length) * 100)}%)</span>
              </div>
              <div className="breakdown-bar-track">
                <div style={{ height: '100%', width: `${(analytics.billing.bulk_billing / practices.length) * 100}%`, background: '#10b981', borderRadius: '9999px' }}></div>
              </div>
            </div>

            <div className="breakdown-item">
              <div className="breakdown-meta">
                <span style={{ color: '#fcd34d' }}>Private Billing Only</span>
                <span>{analytics.billing.private_billing} ({Math.round((analytics.billing.private_billing / practices.length) * 100)}%)</span>
              </div>
              <div className="breakdown-bar-track">
                <div style={{ height: '100%', width: `${(analytics.billing.private_billing / practices.length) * 100}%`, background: '#f59e0b', borderRadius: '9999px' }}></div>
              </div>
            </div>

            <div className="breakdown-item" style={{ marginTop: '8px', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)' }}>
              <div className="breakdown-meta">
                <span style={{ color: 'var(--text-secondary)' }}>Telehealth Consultations</span>
                <span style={{ color: '#38bdf8' }}>
                  {practices.filter(p => Boolean(p.telehealth_available)).length} practices enabled
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Filter & Search Command Center */}
      <section className="glass-panel filter-toolbar">
        <div className="filter-row-top">
          {/* Search Input */}
          <div className="search-box-wrap">
            <Search className="search-icon-inside" size={17} />
            <input
              type="text"
              placeholder="Search by clinic name, suburb, address or 4-digit postcode..."
              className="search-input"
              value={searchQuery}
              onChange={e => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="clear-search-btn">
                <X size={14} />
              </button>
            )}
          </div>

          {/* State Dropdown */}
          <select
            value={selectedState}
            onChange={e => {
              setSelectedState(e.target.value);
              setCurrentPage(1);
            }}
            className="select-filter"
          >
            <option value="ALL">All States (Australia)</option>
            <option value="VIC">VIC ({analytics.states.VIC || 0})</option>
            <option value="NSW">NSW ({analytics.states.NSW || 0})</option>
            <option value="QLD">QLD ({analytics.states.QLD || 0})</option>
            <option value="WA">WA ({analytics.states.WA || 0})</option>
            <option value="SA">SA ({analytics.states.SA || 0})</option>
            <option value="TAS">TAS ({analytics.states.TAS || 0})</option>
            <option value="ACT">ACT ({analytics.states.ACT || 0})</option>
          </select>

          {/* Billing Model Dropdown */}
          <select
            value={selectedBilling}
            onChange={e => {
              setSelectedBilling(e.target.value);
              setCurrentPage(1);
            }}
            className="select-filter"
          >
            <option value="ALL">All Billing Models</option>
            <option value="mixed_billing">Mixed Billing</option>
            <option value="bulk_billing">Bulk Billing Only</option>
            <option value="private_billing">Private Billing Only</option>
          </select>

          {/* Booking Platform Dropdown */}
          <select
            value={selectedPlatform}
            onChange={e => {
              setSelectedPlatform(e.target.value);
              setCurrentPage(1);
            }}
            className="select-filter"
          >
            <option value="ALL">All Booking Software</option>
            <option value="hotdoc">HotDoc</option>
            <option value="healthengine">Healthengine</option>
            <option value="phone_only">Phone-Only Booking</option>
            <option value="other_online">Other Online</option>
          </select>

          {/* Reset Button */}
          <button onClick={resetFilters} className="btn btn-secondary" style={{ padding: '8px 12px' }}>
            <span>Reset</span>
          </button>
        </div>

        {/* Quick Filter Chips */}
        <div className="filter-pills-row">
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600 }}>Quick Filters:</span>

          <button
            onClick={() => {
              setMinScore(prev => (prev === 80 ? 0 : 80));
              setCurrentPage(1);
            }}
            className={`filter-chip ${minScore === 80 ? 'active-high' : ''}`}
          >
            <Sparkles size={12} style={{ display: 'inline', marginRight: '4px' }} />
            High Opportunity (Score ≥ 80)
          </button>

          <button
            onClick={() => {
              setTelehealthOnly(prev => !prev);
              setCurrentPage(1);
            }}
            className={`filter-chip ${telehealthOnly ? 'active' : ''}`}
          >
            Telehealth Available
          </button>

          <button
            onClick={() => {
              setWheelchairOnly(prev => !prev);
              setCurrentPage(1);
            }}
            className={`filter-chip ${wheelchairOnly ? 'active' : ''}`}
          >
            Wheelchair Accessible
          </button>

          <button
            onClick={() => {
              setSelectedBilling(prev => (prev === 'bulk_billing' ? 'ALL' : 'bulk_billing'));
              setCurrentPage(1);
            }}
            className={`filter-chip ${selectedBilling === 'bulk_billing' ? 'active' : ''}`}
          >
            100% Bulk Billed
          </button>

          <button
            onClick={() => {
              setSelectedPlatform(prev => (prev === 'phone_only' ? 'ALL' : 'phone_only'));
              setCurrentPage(1);
            }}
            className={`filter-chip ${selectedPlatform === 'phone_only' ? 'active' : ''}`}
          >
            Phone-Only (High Automation Fit)
          </button>
        </div>
      </section>

      {/* 5. Results Counter Bar */}
      <div className="results-info-bar">
        <div>
          Showing <strong>{paginatedPractices.length}</strong> of <strong>{filteredPractices.length}</strong> matched clinics
          {filteredPractices.length !== practices.length && ` (filtered from ${practices.length} total)`}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>Show per page:</span>
          <select
            value={itemsPerPage}
            onChange={e => {
              setItemsPerPage(Number(e.target.value));
              setCurrentPage(1);
            }}
            className="select-filter"
            style={{ padding: '4px 8px' }}
          >
            <option value="15">15</option>
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>
        </div>
      </div>

      {/* 6. Interactive Data Table */}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('name')}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>Practice / Clinic Name</span>
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th onClick={() => handleSort('state')}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>State & Postcode</span>
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th>Reception Phone</th>
              <th onClick={() => handleSort('billing')}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>Billing Model</span>
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th>Booking Tech</th>
              <th onClick={() => handleSort('score')}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>Opportunity Score</span>
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th style={{ textAlign: 'center' }}>Lead Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedPractices.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '48px 20px', color: 'var(--text-muted)' }}>
                  <Building2 size={36} style={{ margin: '0 auto 12px auto', opacity: 0.4 }} />
                  <p style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text-secondary)' }}>No matching general practices found</p>
                  <p style={{ fontSize: '0.85rem', marginTop: '4px' }}>Try broadening your search criteria or resetting filters.</p>
                  <button onClick={resetFilters} className="btn btn-secondary" style={{ marginTop: '14px' }}>
                    Reset All Filters
                  </button>
                </td>
              </tr>
            ) : (
              paginatedPractices.map(practice => {
                const isHigh = practice.opportunity_score >= 80;
                const isMedium = practice.opportunity_score >= 70 && practice.opportunity_score < 80;
                const scoreColor = isHigh ? '#10b981' : isMedium ? '#06b6d4' : '#94a3b8';

                return (
                  <tr key={practice.practice_id}>
                    {/* Practice Name */}
                    <td>
                      <div style={{ fontWeight: 700, color: 'var(--text-main)', fontSize: '0.9rem' }}>
                        {practice.practice_name}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                        <MapPin size={12} />
                        <span>{practice.suburb}, {practice.state}</span>
                      </div>
                    </td>

                    {/* State & Postcode */}
                    <td>
                      <span className="badge badge-state">{practice.state} {practice.postcode}</span>
                    </td>

                    {/* Phone */}
                    <td>
                      <a
                        href={`tel:${practice.phone_main}`}
                        style={{ color: '#38bdf8', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}
                        title="Click to dial reception"
                      >
                        <Phone size={13} />
                        <span>{practice.phone_main}</span>
                      </a>
                      <div style={{ marginTop: '4px' }}>
                        {practice.phone_verified !== false ? (
                          <span style={{ fontSize: '0.68rem', color: '#34d399', background: 'rgba(16, 185, 129, 0.12)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.25)', display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                            ✓ AI Verified
                          </span>
                        ) : (
                          <span style={{ fontSize: '0.68rem', color: '#f87171', background: 'rgba(239, 68, 68, 0.12)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(239, 68, 68, 0.25)', display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                            ⚠ Unverified
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Billing Model */}
                    <td>
                      <span className={`badge badge-${practice.billing_model.toLowerCase().includes('bulk') ? 'bulk' : practice.billing_model.toLowerCase().includes('mixed') ? 'mixed' : practice.billing_model.toLowerCase().includes('private') ? 'private' : 'unknown'}`}>
                        {practice.billing_model.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>

                    {/* Booking Platform */}
                    <td>
                      <span className={`badge badge-${practice.booking_platform.toLowerCase().includes('hotdoc') ? 'hotdoc' : practice.booking_platform.toLowerCase().includes('healthengine') ? 'healthengine' : 'phone'}`}>
                        {practice.booking_platform.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>

                    {/* Opportunity Score */}
                    <td>
                      <div className="score-pill-wrap">
                        <span className="score-number" style={{ color: scoreColor }}>
                          {practice.opportunity_score}
                        </span>
                        <div className="score-mini-bar">
                          <div className="score-fill" style={{ width: `${practice.opportunity_score}%`, backgroundColor: scoreColor }}></div>
                        </div>
                      </div>
                    </td>

                    {/* Actions */}
                    <td style={{ textAlign: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                        <button
                          onClick={() => setSelectedPractice(practice)}
                          className="btn btn-secondary"
                          style={{ padding: '5px 10px', fontSize: '0.78rem' }}
                        >
                          View Lead
                        </button>

                        {practice.growth_outreach_hook && (
                          <button
                            onClick={() => handleCopy(practice.growth_outreach_hook || '', practice.practice_id)}
                            className="btn-icon"
                            title="Copy Personalized B2B Pitch"
                          >
                            {copyFeedback === practice.practice_id ? <CheckCircle2 size={14} color="#10b981" /> : <Sparkles size={14} />}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* 7. Pagination Controls */}
      {totalPages > 1 && (
        <div className="pagination-bar">
          <div>
            Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong>
          </div>
          <div className="pagination-buttons">
            <button
              onClick={() => setCurrentPage(p => Math.max(p - 1, 1))}
              disabled={currentPage === 1}
              className="page-num-btn"
              style={{ opacity: currentPage === 1 ? 0.4 : 1 }}
            >
              <ChevronLeft size={16} />
            </button>

            {Array.from({ length: Math.min(totalPages, 5) }, (_, idx) => {
              let pageNum = idx + 1;
              if (totalPages > 5 && currentPage > 3) {
                pageNum = currentPage - 2 + idx;
                if (pageNum > totalPages) pageNum = totalPages - 4 + idx;
              }
              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`page-num-btn ${currentPage === pageNum ? 'active' : ''}`}
                >
                  {pageNum}
                </button>
              );
            })}

            <button
              onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))}
              disabled={currentPage === totalPages}
              className="page-num-btn"
              style={{ opacity: currentPage === totalPages ? 0.4 : 1 }}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* 8. Practice Lead Detail Drawer / Modal */}
      {selectedPractice && (
        <div className="modal-overlay" onClick={() => setSelectedPractice(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <button onClick={() => setSelectedPractice(null)} className="modal-close-btn">
              <X size={18} />
            </button>

            {/* Header info */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', paddingRight: '36px', marginBottom: '18px' }}>
              <div>
                <span className="badge badge-state" style={{ marginBottom: '6px' }}>
                  {selectedPractice.state} {selectedPractice.postcode}
                </span>
                <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
                  {selectedPractice.practice_name}
                </h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}>
                  <MapPin size={14} color="#6366f1" />
                  <span>{selectedPractice.practice_address}</span>
                </p>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>OPPORTUNITY FIT</div>
                <div style={{ fontSize: '2rem', fontWeight: 900, color: selectedPractice.opportunity_score >= 80 ? '#10b981' : '#06b6d4', lineHeight: 1.1 }}>
                  {selectedPractice.opportunity_score}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Score Index</div>
              </div>
            </div>

            {/* Details Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '20px' }}>
              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>RECEPTION PHONE</span>
                <a href={`tel:${selectedPractice.phone_main}`} style={{ color: '#38bdf8', textDecoration: 'none', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.9rem' }}>
                  <Phone size={14} />
                  <span>{selectedPractice.phone_main}</span>
                </a>
                <div style={{ marginTop: '6px', fontSize: '0.74rem', color: selectedPractice.phone_verified !== false ? '#34d399' : '#f87171', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span>{selectedPractice.phone_verified !== false ? '✓ AI Verified Line' : '⚠ Unverified Number'}</span>
                  {selectedPractice.phone_type && (
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.70rem' }}>({selectedPractice.phone_type})</span>
                  )}
                </div>
                {selectedPractice.phone_verification_notes && (
                  <div style={{ fontSize: '0.70rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                    {selectedPractice.phone_verification_notes}
                  </div>
                )}
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>OFFICIAL WEBSITE</span>
                {selectedPractice.website_url ? (
                  <a href={selectedPractice.website_url} target="_blank" rel="noopener noreferrer" style={{ color: '#818cf8', textDecoration: 'none', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem' }}>
                    <Globe size={14} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '170px' }}>{selectedPractice.website_url}</span>
                    <ExternalLink size={12} />
                  </a>
                ) : (
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Not Listed</span>
                )}
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>MEDICARE BILLING</span>
                <span className={`badge badge-${selectedPractice.billing_model.toLowerCase().includes('bulk') ? 'bulk' : selectedPractice.billing_model.toLowerCase().includes('mixed') ? 'mixed' : 'private'}`}>
                  {selectedPractice.billing_model.replace('_', ' ').toUpperCase()}
                </span>
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>BOOKING SOFTWARE</span>
                <span className="badge badge-hotdoc">
                  {selectedPractice.booking_platform.replace('_', ' ').toUpperCase()}
                </span>
              </div>
            </div>

            {/* Operational Signals */}
            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '14px 16px', borderRadius: '10px', border: '1px solid var(--border-subtle)', marginBottom: '18px' }}>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Clock size={14} />
                <span>Operating Hours & Accessibility Signals</span>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-main)', marginBottom: '10px' }}>
                {selectedPractice.opening_hours_summary || 'Standard Business Hours (Monday - Friday)'}
              </p>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <span className="badge" style={{ background: selectedPractice.telehealth_available ? 'rgba(16, 185, 129, 0.12)' : 'rgba(100, 116, 139, 0.1)', color: selectedPractice.telehealth_available ? '#34d399' : '#94a3b8' }}>
                  {selectedPractice.telehealth_available ? '✓ Telehealth Enabled' : '✗ In-Clinic Only'}
                </span>
                <span className="badge" style={{ background: selectedPractice.wheelchair_accessible ? 'rgba(6, 182, 212, 0.12)' : 'rgba(100, 116, 139, 0.1)', color: selectedPractice.wheelchair_accessible ? '#38bdf8' : '#94a3b8' }}>
                  {selectedPractice.wheelchair_accessible ? '✓ Wheelchair Accessible' : 'Standard Access'}
                </span>
                <span className="badge" style={{ background: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-secondary)' }}>
                  Confidence: {Math.round(selectedPractice.ai_confidence_score * 100)}%
                </span>
              </div>
            </div>

            {/* Billing Evidence Citation */}
            {selectedPractice.billing_model_evidence && (
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '14px', padding: '0 4px' }}>
                <strong>Evidence Citation:</strong> {selectedPractice.billing_model_evidence}
              </div>
            )}

            {/* Personalized B2B Outreach Hook */}
            {selectedPractice.growth_outreach_hook && (
              <div className="growth-hook-box">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#818cf8', fontWeight: 700, fontSize: '0.82rem', marginBottom: '8px' }}>
                  <Sparkles size={15} />
                  <span>AI Automated B2B Outreach Pitch</span>
                </div>
                <p className="hook-text">"{selectedPractice.growth_outreach_hook}"</p>
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    onClick={() => handleCopy(selectedPractice.growth_outreach_hook || '', 'modal-hook')}
                    className="btn btn-primary"
                    style={{ padding: '6px 14px', fontSize: '0.8rem' }}
                  >
                    {copyFeedback === 'modal-hook' ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                    <span>{copyFeedback === 'modal-hook' ? 'Pitch Copied!' : 'Copy Outreach Hook'}</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 9. Architecture & Compliance Modal */}
      {showArchitectureModal && (
        <div className="modal-overlay" onClick={() => setShowArchitectureModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <button onClick={() => setShowArchitectureModal(false)} className="modal-close-btn">
              <X size={18} />
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
              <ShieldCheck size={24} color="#10b981" />
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)' }}>
                System Architecture & Legal Compliance
              </h2>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '0.85rem', color: '#cbd5e1' }}>
              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <h4 style={{ color: '#38bdf8', fontWeight: 700, marginBottom: '4px' }}>1. 8-Stage Extraction Pipeline</h4>
                <p style={{ color: 'var(--text-secondary)' }}>
                  Geographic Discovery ➔ Playwright Stealth Scraping ➔ Cleaning & E.164 Normalization ➔ Pydantic Schema Validation ➔ SHA256 Deduplication ➔ LLM Growth Intelligence ➔ SQLite WAL Checkpoints ➔ Streaming CSV/JSON Exports.
                </p>
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <h4 style={{ color: '#34d399', fontWeight: 700, marginBottom: '4px' }}>2. Australian Privacy Act 1988 (APPs)</h4>
                <p style={{ color: 'var(--text-secondary)' }}>
                  Strict practice-level focus. The pipeline explicitly detects and strips doctor personal names, practitioner bios, headshots, and personal staff emails to prevent harvesting identifiable individuals.
                </p>
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <h4 style={{ color: '#fb923c', fontWeight: 700, marginBottom: '4px' }}>3. Spam Act 2003 & Rate Limiting</h4>
                <p style={{ color: 'var(--text-secondary)' }}>
                  No personal email harvesting. Crawling operates at concurrency = 1 with randomized jitter (2.5s–4.5s) and automated circuit breakers upon encountering HTTP 429 or 403 restrictions.
                </p>
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <h4 style={{ color: '#a5b4fc', fontWeight: 700, marginBottom: '4px' }}>4. AI Growth Opportunity Scorer (0–100)</h4>
                <p style={{ color: 'var(--text-secondary)' }}>
                  B2B commercial fit is computed from billing dynamics, online software adoption (HotDoc/Healthengine vs phone-only), extended hours, and telehealth support to pinpoint top-tier outreach opportunities.
                </p>
              </div>
            </div>

            <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end' }}>
              <button onClick={() => setShowArchitectureModal(false)} className="btn btn-secondary">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
