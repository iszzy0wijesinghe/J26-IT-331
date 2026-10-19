import React from 'react';

interface ScenarioButtonsProps {
  onRunScenario: (scenario: string) => void;
  onClearResults: () => void;
}

export const ScenarioButtons: React.FC<ScenarioButtonsProps> = ({ onRunScenario, onClearResults }) => {
  
  // Shared styles for the nested dropdowns
  const nestedDropdownStyle: React.CSSProperties = {
    background: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    marginBottom: '12px',
    overflow: 'hidden'
  };

  const nestedSummaryStyle: React.CSSProperties = {
    padding: '12px 16px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
    color: '#334155',
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#f8fafc'
  };

  const buttonGroupStyle: React.CSSProperties = {
    padding: '16px',
    borderTop: '1px solid #e2e8f0',
    display: 'flex',
    flexWrap: 'wrap',
    gap: '12px'
  };

  // Reusable button styles
  const btnStyle: React.CSSProperties = {
    padding: '8px 16px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    border: '1px solid #cbd5e1',
    background: 'white',
    color: '#1e293b'
  };

  const btnDangerStyle: React.CSSProperties = {
    ...btnStyle,
    borderColor: '#fca5a5',
    color: '#b91c1c',
    background: '#fef2f2'
  };

  const btnSuccessStyle: React.CSSProperties = {
    ...btnStyle,
    borderColor: '#86efac',
    color: '#15803d',
    background: '#f0fdf4'
  };

  return (
    <div>
      {/* HMAC DROPDOWN */}
      <details style={nestedDropdownStyle}>
        <summary style={nestedSummaryStyle}>
          <span style={{ marginRight: '8px', color: '#14b8a6' }}>▶</span> HMAC
        </summary>
        <div style={buttonGroupStyle}>
          <button style={btnSuccessStyle} onClick={() => onRunScenario('Run Valid Telemetry (HMAC)')}>
            Run Valid Telemetry
          </button>
          <button style={btnDangerStyle} onClick={() => onRunScenario('Test Tampered')}>
            Test Tampered
          </button>
          <button style={btnDangerStyle} onClick={() => onRunScenario('Test Replay Attack')}>
            Test Replay Attack
          </button>
        </div>
      </details>

      {/* ECDSA DROPDOWN */}
      <details style={nestedDropdownStyle}>
        <summary style={nestedSummaryStyle}>
          <span style={{ marginRight: '8px', color: '#14b8a6' }}>▶</span> ECDSA
        </summary>
        <div style={buttonGroupStyle}>
          <button style={btnSuccessStyle} onClick={() => onRunScenario('Run Valid X.509 + ECDSA')}>
            Run Valid X.509 + ECDSA
          </button>
          <button style={btnDangerStyle} onClick={() => onRunScenario('Test Tampered ECDSA')}>
            Test Tampered
          </button>
          <button style={btnDangerStyle} onClick={() => onRunScenario('Test Alg Fallback Rejection')}>
            Test Alg Fallback Rejection
          </button>
        </div>
      </details>

      {/* CERT DROPDOWN */}
      <details style={nestedDropdownStyle}>
        <summary style={nestedSummaryStyle}>
          <span style={{ marginRight: '8px', color: '#14b8a6' }}>▶</span> CERT
        </summary>
        <div style={buttonGroupStyle}>
          <button style={btnDangerStyle} onClick={() => onRunScenario('Test Expired')}>
            Expired
          </button>
          <button style={btnDangerStyle} onClick={() => onRunScenario('Test Untrusted CA')}>
            Untrusted CA
          </button>
          <button style={btnDangerStyle} onClick={() => onRunScenario('Test Identity Mismatch Cert')}>
            Identity Mismatch Cert
          </button>
          <button style={btnDangerStyle} onClick={() => onRunScenario('Test Revoked')}>
            Revoked
          </button>
        </div>
      </details>

      {/* CLEAR BUTTON */}
      <div style={{ marginTop: '24px', textAlign: 'right' }}>
        <button 
          style={{ ...btnStyle, background: '#f1f5f9' }} 
          onClick={onClearResults}
        >
          Clear Results
        </button>
      </div>
    </div>
  );
};