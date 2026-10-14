import { useState } from 'react';
import { App as AntApp, Button, Input, Typography, Upload } from 'antd';
import { CopyOutlined, DownloadOutlined, ExclamationCircleOutlined, ReloadOutlined, UploadOutlined } from '@ant-design/icons';
import { api, getApiErrorMessage } from '../config/auth.js';

function macPairs(raw) {
  const hex = String(raw || '').replace(/[^a-fA-F0-9]/g, '').toUpperCase();
  return hex.match(/.{1,2}/g)?.slice(0, 6) || [];
}

function fullMac(raw) {
  const pairs = macPairs(raw);
  return pairs.length === 6 ? pairs.join(':') : '';
}

function maskedMac(raw) {
  const pairs = macPairs(raw);
  if (pairs.length !== 6) return '—';
  return pairs.map((pair, index) => (index === 0 || index === pairs.length - 1 ? pair : '**')).join(':');
}

function daysRemaining(expiry) {
  if (!expiry) return 0;
  const end = new Date(expiry);
  if (Number.isNaN(end.getTime())) return 0;
  const diff = end.getTime() - Date.now();
  return Math.max(0, Math.ceil(diff / 86400000));
}

export default function LicenseActivation({ status, onActivated }) {
  const { message } = AntApp.useApp();
  const [machine, setMachine] = useState(null);
  const [credentialsText, setCredentialsText] = useState('');
  const [licenseText, setLicenseText] = useState('');
  const [licenseUploaded, setLicenseUploaded] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [activating, setActivating] = useState(false);

  const remaining = daysRemaining(status?.expiry);
  const inactive = !status?.licensed;

  const fetchCredentials = async () => {
    setFetching(true);
    try {
      const { data } = await api.get('/license/machine-request');
      setMachine(data);
      setCredentialsText(JSON.stringify(data, null, 2));
      message.success('Hardware request loaded');
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Could not read this computer'));
    } finally {
      setFetching(false);
    }
  };

  const copyMac = async () => {
    const mac = fullMac(machine?.MacAddress);
    if (!mac) {
      message.warning('Fetch the hardware request first');
      return;
    }
    try {
      await navigator.clipboard.writeText(mac);
      message.success('MAC address copied');
    } catch {
      message.error('Could not copy the MAC address');
    }
  };

  const activate = async () => {
    setActivating(true);
    try {
      const { data } = await api.post('/license/activate', { license_text: licenseText });
      message.success('License activated for this computer');
      onActivated(data);
    } catch (error) {
      message.error(getApiErrorMessage(error, 'Could not activate license'));
    } finally {
      setActivating(false);
    }
  };

  const downloadAsTxt = () => {
    if (!machine) {
      message.warning('Fetch the hardware request first');
      return;
    }
    const content = credentialsText;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'hardware_request.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    message.success('Downloaded as TXT');
  };

  const handleFileUpload = (file) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target.result;
      setLicenseText(content);
      setLicenseUploaded(true);
      message.success('License file loaded');
    };
    reader.onerror = () => {
      message.error('Failed to read file');
    };
    reader.readAsText(file);
    return false;
  };

  const clearLicense = () => {
    setLicenseText('');
    setLicenseUploaded(false);
  };

  return (
    <div className="relative z-10 mx-auto w-full max-w-3xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-start gap-3 bg-teal-600 px-6 py-4 text-white">
        <ExclamationCircleOutlined className="mt-1 text-lg text-teal-200" />
        <div>
          <Typography.Title level={4} className="!mb-0 !font-sans !text-white">
            Software license required
          </Typography.Title>
          <Typography.Text className="text-teal-100">
            Sign-in stays closed until a valid license is activated on this computer.
          </Typography.Text>
        </div>
      </div>

      <div className="space-y-4 px-6 py-5">
        <div>
          <p className="mb-2 text-xs font-semibold tracking-wide text-slate-500">
            HOST MACHINE SYSTEM MAC ADDRESS
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <div className="min-w-[220px] flex-1 rounded-lg border border-slate-200 bg-slate-50 px-4 py-2 font-mono text-lg tracking-widest text-slate-800">
              {maskedMac(machine?.MacAddress)}
            </div>
            <Button
              icon={<ReloadOutlined />}
              loading={fetching}
              onClick={fetchCredentials}
              className="!rounded-full !border-teal-600 !text-teal-700"
            >
              Fetch credentials
            </Button>
            <Button icon={<CopyOutlined />} onClick={copyMac} className="!rounded-full">
              Copy MAC
            </Button>
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-slate-200">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-slate-50 px-4 py-2">
            <span className="text-sm font-semibold text-slate-800">Fetched hardware request</span>
            <Button
              size="small"
              type="primary"
              icon={<DownloadOutlined />}
              onClick={downloadAsTxt}
              className="!rounded-full !bg-teal-600 hover:!bg-teal-700"
            >
              Download
            </Button>
          </div>
          <Input.TextArea
            readOnly
            value={credentialsText}
            placeholder="Click Fetch to load this computer's hardware request. Send that text to your vendor."
            autoSize={{ minRows: 5, maxRows: 8 }}
            className="!rounded-none !border-0 !font-mono !text-xs !shadow-none"
          />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
          <span className="text-sm text-slate-700">
            Current status:{' '}
            <span className={inactive ? 'font-semibold text-rose-600' : 'font-semibold text-teal-700'}>
              {inactive ? 'License inactive / expired' : 'License active'}
            </span>
          </span>
          <span className="text-sm font-medium text-slate-600">
            {remaining} {remaining === 1 ? 'day' : 'days'} remaining
          </span>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-medium text-slate-700">Paste or Upload the signed license</p>
            <div className="flex items-center gap-2">
              {licenseUploaded && (
                <Button size="small" onClick={clearLicense} className="!rounded-full">
                  Clear
                </Button>
              )}
              <Upload
                accept=".txt"
                showUploadList={false}
                beforeUpload={handleFileUpload}
              >
                <Button icon={<UploadOutlined />} size="small" className="!rounded-full">
                  Upload file
                </Button>
              </Upload>
            </div>
          </div>
          <Input.TextArea
            value={licenseText}
            onChange={(event) => {
              setLicenseText(event.target.value);
              setLicenseUploaded(false);
            }}
            readOnly={licenseUploaded}
            placeholder="Paste the signed license JSON here or upload a file"
            autoSize={{ minRows: 4, maxRows: 8 }}
            className="!font-mono !text-xs"
          />
        </div>

        <Button
          type="primary"
          size="large"
          block
          loading={activating}
          disabled={!licenseText.trim()}
          onClick={activate}
          className="!h-11 !rounded-full !bg-teal-600 !font-semibold hover:!bg-teal-700"
        >
          Activate license
        </Button>
      </div>
    </div>
  );
}
