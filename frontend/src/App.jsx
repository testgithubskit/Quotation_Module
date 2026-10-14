import { useEffect, useState } from 'react';
import { App as AntApp, ConfigProvider, Spin } from 'antd';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, homePathForUser, useAuth } from './config/AuthContext.jsx';
import { installAutofillGuard } from './utils/disableAutofill.js';
import { api } from './config/auth.js';
import LicenseActivation from './Components/LicenseActivation.jsx';
import Login from './Pages/Login';
import Admin from './Pages/Admin';
import User from './Pages/User';
import DotField from './Components/DotField';

function LicenseGate({ children }) {
  const [licenseState, setLicenseState] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api.get('/license/status')
      .then((response) => {
        if (!cancelled) setLicenseState(response.data);
      })
      .catch(() => {
        if (!cancelled) setLicenseState({ licensed: false, mac: '', days_remaining: 0 });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (licenseState === null) {
    return (
      <div className="grid min-h-screen place-items-center bg-[#eef1f4]">
        <Spin size="large" />
      </div>
    );
  }

  if (!licenseState.licensed) {
    return (
      <div className="relative flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10 font-sans overflow-hidden">
        <div className="absolute inset-0 z-0">
          <DotField
            dotRadius={3.5}
            dotSpacing={12}
            bulgeStrength={67}
            glowRadius={80}
            sparkle={false}
            waveAmplitude={0}
            bulgeOnly={false}
            gradientFrom="#0D9488"
            gradientTo="#84CC16"
            glowColor="#0D9488"
          />
        </div>
        <LicenseActivation status={licenseState} onActivated={setLicenseState} />
      </div>
    );
  }

  return children;
}

function AppRoutes() {
  const { user, booting, isAuthenticated } = useAuth();

  if (booting) {
    return (
      <div className="grid min-h-screen place-items-center">
        <Spin size="large" />
      </div>
    );
  }

  const home = homePathForUser(user);

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to={home} replace /> : <Login />}
      />
      <Route path="/admin/*" element={<Admin />} />
      <Route path="/user/*" element={<User />} />
      <Route path="/" element={<Navigate to={home} replace />} />
      <Route path="*" element={<Navigate to={home} replace />} />
    </Routes>
  );
}

export default function App() {
  useEffect(() => installAutofillGuard(), []);

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#0D9488',
          colorInfo: '#0D9488',
          colorBgLayout: '#F1F5F9',
          colorBorder: '#CBD5E1',
          colorText: '#0F172A',
          borderRadius: 8,
          fontFamily: "'Inter', ui-sans-serif, system-ui, sans-serif",
        },
        components: {
          Layout: {
            siderBg: '#134E4A',
            bodyBg: '#F1F5F9',
          },
          Menu: {
            darkItemBg: 'transparent',
            darkItemSelectedBg: '#0D9488',
          },
        },
      }}
    >
      <AntApp>
        <AuthProvider>
          <BrowserRouter>
            <LicenseGate>
              <AppRoutes />
            </LicenseGate>
          </BrowserRouter>
        </AuthProvider>
      </AntApp>
    </ConfigProvider>
  );
}
