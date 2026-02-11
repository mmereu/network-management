import { useState, useRef, useEffect } from 'react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Server, Play, Square, TrendingUp, CheckCircle, XCircle, Clock } from 'lucide-react';

interface SwitchStatus {
  ip: string;
  status: 'pending' | 'running' | 'success' | 'error' | 'failed';
  progress: number;
  message: string;
  startTime?: Date;
  endTime?: Date;
  execution_time?: number;
}

interface ApiLog {
  timestamp: string;
  level: string;
  message: string;
}

interface ApiSwitchResult {
  switch_ip: string;
  switch_name: string;
  status: string;
  execution_time: number | null;
  start_time?: string;
  error_message?: string | null;
}

// API base URL - uses relative path for production
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export function ConfigSwitchPage() {
  const [ipList, setIpList] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [commands, setCommands] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [switches, setSwitches] = useState<SwitchStatus[]>([]);
  const [globalProgress, setGlobalProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [processId, setProcessId] = useState<string | null>(null);
  const monitorIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const displayedLogCountRef = useRef(0);

  const stats = {
    total: switches.length,
    success: switches.filter(s => s.status === 'success').length,
    error: switches.filter(s => s.status === 'error').length,
    pending: switches.filter(s => s.status === 'pending' || s.status === 'running').length,
  };

  const handleStart = async () => {
    const ips = ipList.split('\n').filter(ip => ip.trim());
    const cmds = commands.split('\n').filter(cmd => cmd.trim());

    // Reset state
    setSwitches([]);
    setGlobalProgress(0);
    setLogs([]);
    displayedLogCountRef.current = 0;
    addLog('⚡ Avvio configurazione massiva...');

    try {
      // Call API to start execution
      const response = await fetch(`${API_BASE_URL}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          hosts: ips,
          username: username,
          password: password,
          commands: cmds
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.success && data.process_id) {
        setProcessId(data.process_id);
        setIsRunning(true);
        addLog(`✅ ${data.message || 'Processo avviato'}`);
        startMonitoring(data.process_id);
      } else {
        throw new Error(data.error || 'Errore avvio processo');
      }
    } catch (error) {
      addLog(`❌ Errore: ${error instanceof Error ? error.message : 'Errore sconosciuto'}`, 'error');
      setIsRunning(false);
    }
  };

  const startMonitoring = (procId: string) => {
    // Clear any existing interval
    if (monitorIntervalRef.current) {
      clearInterval(monitorIntervalRef.current);
    }

    // Start polling every 1 second
    monitorIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/status/${procId}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Update progress
        setGlobalProgress(data.progress || 0);

        // Add new logs
        if (data.logs && data.logs.length > displayedLogCountRef.current) {
          const newLogs = data.logs.slice(displayedLogCountRef.current);
          newLogs.forEach((log: ApiLog) => {
            addLog(`${log.message}`, log.level);
          });
          displayedLogCountRef.current = data.logs.length;
        }

        // Update switch cards
        if (data.switch_results) {
          const updatedSwitches: SwitchStatus[] = data.switch_results.map((result: ApiSwitchResult) => {
            const normalizedStatus = result.status === 'failed' ? 'error' :
                                    (result.status as 'pending' | 'running' | 'success' | 'error');
            return {
              ip: result.switch_ip,
              status: normalizedStatus,
              progress: normalizedStatus === 'success' || normalizedStatus === 'error' ? 100 :
                       normalizedStatus === 'running' ? 50 : 0,
              message: normalizedStatus === 'success' ? 'Configurato' :
                      normalizedStatus === 'error' ? (result.error_message || 'Errore') :
                      normalizedStatus === 'running' ? 'In esecuzione...' : 'In coda...',
              execution_time: result.execution_time || undefined,
              startTime: result.start_time ? new Date(result.start_time) : undefined,
            };
          });
          setSwitches(updatedSwitches);
        }

        // Check completion
        if (data.status === 'completed' || data.status === 'error') {
          stopMonitoring();
          setIsRunning(false);
          addLog(data.status === 'completed' ? '✅ Configurazione completata!' : '❌ Errore durante l\'esecuzione');
        }

      } catch (error) {
        console.error('Error polling status:', error);
        addLog(`⚠️ Errore monitoraggio: ${error instanceof Error ? error.message : 'Errore sconosciuto'}`, 'warning');
      }
    }, 1000);
  };

  const stopMonitoring = () => {
    if (monitorIntervalRef.current) {
      clearInterval(monitorIntervalRef.current);
      monitorIntervalRef.current = null;
    }
  };

  const handleStop = async () => {
    if (!processId) return;

    try {
      await fetch(`${API_BASE_URL}/stop/${processId}`, {
        method: 'POST',
      });
      stopMonitoring();
      setIsRunning(false);
      addLog('⏹️ Operazione interrotta dall\'utente');
    } catch (error) {
      addLog(`❌ Errore interruzione: ${error instanceof Error ? error.message : 'Errore sconosciuto'}`, 'error');
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopMonitoring();
    };
  }, []);

  const addLog = (message: string, _level?: string) => {
    const timestamp = new Date().toLocaleTimeString('it-IT');
    setLogs(prev => [`[${timestamp}] ${message}`, ...prev].slice(0, 100));
  };

  const getStatusColor = (status: SwitchStatus['status']) => {
    switch (status) {
      case 'success': return 'text-green-400 border-green-500/30 bg-green-500/10';
      case 'error': return 'text-red-400 border-red-500/30 bg-red-500/10';
      case 'running': return 'text-blue-400 border-blue-500/30 bg-blue-500/10';
      default: return 'text-gray-400 border-gray-500/30 bg-gray-500/10';
    }
  };

  const getStatusIcon = (status: SwitchStatus['status']) => {
    switch (status) {
      case 'success': return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'error': return <XCircle className="w-5 h-5 text-red-400" />;
      case 'running': return <Clock className="w-5 h-5 text-blue-400 animate-spin" />;
      default: return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-3">
            <Server className="w-8 h-8 text-purple-400" />
            <h1 className="text-3xl font-bold text-white">ConfigSwitch</h1>
          </div>
          <p className="text-gray-400">Configurazione Massiva Switch di Rete con Advanced Monitoring</p>
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* LEFT COLUMN - Configuration */}
          <Card className="p-6 bg-slate-900/50 backdrop-blur-xl border-purple-500/20">
            <div className="flex items-center gap-2 mb-4">
              <Server className="w-5 h-5 text-purple-400" />
              <h2 className="text-xl font-bold text-white">Configurazione</h2>
            </div>

            <div className="space-y-4">
              {/* IP List */}
              <div className="space-y-2">
                <Label className="text-white flex items-center gap-2">
                  <Server className="w-4 h-4" />
                  Indirizzi IP Switch (uno per riga)
                </Label>
                <textarea
                  value={ipList}
                  onChange={(e) => setIpList(e.target.value)}
                  placeholder="192.168.1.10&#10;192.168.1.11&#10;192.168.1.12"
                  className="w-full h-24 px-4 py-2 bg-slate-800/50 border border-purple-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none font-mono text-sm"
                  disabled={isRunning}
                />
              </div>

              {/* Credentials */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-white">Username SSH</Label>
                  <Input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="admin"
                    className="bg-slate-800/50 border-purple-500/20 text-white"
                    disabled={isRunning}
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-white">Password SSH</Label>
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="bg-slate-800/50 border-purple-500/20 text-white"
                    disabled={isRunning}
                  />
                </div>
              </div>

              {/* Commands */}
              <div className="space-y-2">
                <Label className="text-white">Comandi di Configurazione</Label>
                <textarea
                  value={commands}
                  onChange={(e) => setCommands(e.target.value)}
                  placeholder="configure terminal&#10;vlan 100&#10;name VLAN_TEST&#10;exit&#10;write memory"
                  className="w-full h-32 px-4 py-2 bg-slate-800/50 border border-purple-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none font-mono text-sm"
                  disabled={isRunning}
                />
              </div>

              {/* Action Buttons */}
              <div className="flex gap-4 pt-2">
                {!isRunning ? (
                  <Button
                    onClick={handleStart}
                    className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-semibold py-3"
                    disabled={!ipList || !username || !password}
                  >
                    <Play className="w-5 h-5 mr-2" />
                    Esegui Configurazione
                  </Button>
                ) : (
                  <Button
                    onClick={handleStop}
                    variant="destructive"
                    className="flex-1 py-3"
                  >
                    <Square className="w-5 h-5 mr-2" />
                    Interrompi
                  </Button>
                )}
              </div>
            </div>
          </Card>

          {/* RIGHT COLUMN - Monitoring */}
          <Card className="p-6 bg-slate-900/50 backdrop-blur-xl border-blue-500/20">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-blue-400" />
              <h2 className="text-xl font-bold text-white">Monitoraggio Operazioni</h2>
            </div>

            {/* Progress Bar */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-300 text-sm">
                  {switches.length > 0 ? (isRunning ? 'In esecuzione...' : 'Completato') : 'Pronto per l\'esecuzione'}
                </span>
                {switches.length > 0 && (
                  <span className="text-blue-400 font-bold">{Math.round(globalProgress)}%</span>
                )}
              </div>
              <div className="relative h-3 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500 rounded-full"
                  style={{ width: `${globalProgress}%` }}
                />
              </div>
            </div>

            {/* Log Panel */}
            <div className="bg-slate-950/80 rounded-lg p-4 h-96 overflow-y-auto font-mono text-sm border border-slate-700/50">
              {logs.length > 0 ? (
                logs.map((log, index) => (
                  <div key={index} className="text-gray-300 py-1">
                    {log}
                  </div>
                ))
              ) : (
                <div className="text-gray-500 flex items-center justify-center h-full">
                  <div className="text-center">
                    <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>In attesa di avvio configurazione...</p>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Statistics - Only show when running/completed */}
        {switches.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="p-4 bg-slate-900/50 backdrop-blur-xl border-purple-500/20">
              <div className="flex items-center gap-3">
                <Server className="w-8 h-8 text-purple-400" />
                <div>
                  <p className="text-2xl font-bold text-white">{stats.total}</p>
                  <p className="text-sm text-gray-400">Totale</p>
                </div>
              </div>
            </Card>
            <Card className="p-4 bg-slate-900/50 backdrop-blur-xl border-green-500/20">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-8 h-8 text-green-400" />
                <div>
                  <p className="text-2xl font-bold text-white">{stats.success}</p>
                  <p className="text-sm text-gray-400">Successi</p>
                </div>
              </div>
            </Card>
            <Card className="p-4 bg-slate-900/50 backdrop-blur-xl border-red-500/20">
              <div className="flex items-center gap-3">
                <XCircle className="w-8 h-8 text-red-400" />
                <div>
                  <p className="text-2xl font-bold text-white">{stats.error}</p>
                  <p className="text-sm text-gray-400">Errori</p>
                </div>
              </div>
            </Card>
            <Card className="p-4 bg-slate-900/50 backdrop-blur-xl border-blue-500/20">
              <div className="flex items-center gap-3">
                <TrendingUp className="w-8 h-8 text-blue-400" />
                <div>
                  <p className="text-2xl font-bold text-white">{stats.pending}</p>
                  <p className="text-sm text-gray-400">In Coda</p>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Switch Cards Grid - Only show when running/completed */}
        {switches.length > 0 && (
          <Card className="p-6 bg-slate-900/50 backdrop-blur-xl border-purple-500/20">
            <h3 className="text-xl font-bold text-white mb-4">Stato Switch</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {switches.map((sw, index) => (
                <div
                  key={index}
                  className={`p-4 rounded-lg border backdrop-blur-sm ${getStatusColor(sw.status)}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono font-semibold">{sw.ip}</span>
                    {getStatusIcon(sw.status)}
                  </div>
                  <p className="text-sm opacity-80">{sw.message}</p>
                  {sw.status === 'running' && (
                    <div className="mt-2 h-1 bg-slate-700 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 animate-pulse" style={{ width: '100%' }} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
