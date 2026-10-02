import React, { useState } from 'react';
import { ShieldCheck, AlertOctagon, RefreshCw, Hash } from 'lucide-react';
import { LedgerReport } from '../../types';

interface LedgerStatusProps {
  ledgerReport: LedgerReport | null;
  onVerifyLedger: () => Promise<void>;
}

export const LedgerStatus: React.FC<LedgerStatusProps> = ({
  ledgerReport,
  onVerifyLedger,
}) => {
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
  const checkedCount = ledgerReport?.checked ?? 0;

  return (
    <div className={`verification-banner ${isChainValid ? 'valid' : 'invalid'}`}>
      <div className="flex items-center gap-3">
        <div className={`banner-icon-box ${isChainValid ? 'text-emerald' : 'text-rose'}`}>
          {isChainValid ? <ShieldCheck size={24} /> : <AlertOctagon size={24} />}
        </div>
        <div>
          <div className="banner-title font-semibold text-sm">
            {isChainValid
              ? 'Cryptographic Hash-Chain Verified'
              : 'Ledger Hash Tampering / Verification Failure Detected!'}
          </div>
          <div className="banner-subtitle text-xs text-secondary font-mono flex items-center gap-2">
            <span>
              <Hash size={11} className="inline mr-0.5 text-muted" />
              {checkedCount} event blocks mathematically verified
            </span>
            {errorCount > 0 && (
              <span className="text-rose font-bold">
                • {errorCount} integrity error(s) found!
              </span>
            )}
          </div>
        </div>
      </div>

      <button
        className="btn btn-secondary btn-sm"
        onClick={handleVerify}
        disabled={verifying}
        title="Re-audit all block hashes against the Supabase database"
      >
        <RefreshCw size={13} className={verifying ? 'animate-spin text-accent' : 'text-secondary'} />
        <span className="text-xs font-mono">{verifying ? 'Auditing SHA-256...' : 'Audit Ledger Proof'}</span>
      </button>
    </div>
  );
};
