import React, { useState } from 'react';
import { ShieldCheck, AlertOctagon, CheckCircle2, RefreshCw } from 'lucide-react';

export default function LedgerStatus({ ledgerReport, onVerifyLedger }) {
  const [verifying, setVerifying] = useState(false);

  const handleVerify = async () => {
    setVerifying(true);
    try {
      await onVerifyLedger();
    } finally {
      setVerifying(false);
    }
  };

  const isChainValid = ledgerReport?.chain_valid ?? true;
  const errorCount = ledgerReport?.errors?.length ?? 0;

  return (
    <div className={`verification-banner ${isChainValid ? 'valid' : 'invalid'}`}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {isChainValid ? (
          <CheckCircle2 size={24} style={{ color: '#10b981' }} />
        ) : (
          <AlertOctagon size={24} style={{ color: '#f43f5e' }} />
        )}
        <div>
          <div style={{ fontWeight: 600, fontSize: '0.9375rem', color: isChainValid ? '#34d399' : '#fb7185' }}>
            {isChainValid ? 'Ledger Chain Mathematically Verified' : 'Integrity Violation Detected in Ledger!'}
          </div>
          <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            {ledgerReport?.checked ?? 0} events verified across SHA-256 hash chains. {errorCount > 0 && `${errorCount} errors detected.`}
          </div>
        </div>
      </div>

      <button
        className="btn btn-secondary btn-sm"
        onClick={handleVerify}
        disabled={verifying}
      >
        <RefreshCw size={12} className={verifying ? 'animate-spin' : ''} />
        <span>{verifying ? 'Verifying Chain...' : 'Verify Cryptographic Chain'}</span>
      </button>
    </div>
  );
}
