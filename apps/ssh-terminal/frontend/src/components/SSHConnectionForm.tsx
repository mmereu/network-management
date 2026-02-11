"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Server, Hash, User, Lock, Eye, EyeOff, CheckCircle2, AlertCircle } from 'lucide-react';
import { GlowEffect } from './GlowEffect';
import { BGPattern } from './BGPattern';

export interface SSHCredentials {
  hostname: string;
  port: string;
  username: string;
  password: string;
}

interface SSHConnectionFormProps {
  onConnect: (credentials: SSHCredentials) => Promise<void>;
  isConnecting?: boolean;
}

interface ValidationState {
  hostname: boolean | null;
  port: boolean | null;
  username: boolean | null;
  password: boolean | null;
}

export const SSHConnectionForm: React.FC<SSHConnectionFormProps> = ({
  onConnect,
  isConnecting = false
}) => {
  const [formData, setFormData] = useState<SSHCredentials>({
    hostname: '',
    port: '22',
    username: '',
    password: '',
  });

  const [showPassword, setShowPassword] = useState(false);
  const [validation, setValidation] = useState<ValidationState>({
    hostname: null,
    port: null,
    username: null,
    password: null,
  });

  const validateHostname = (value: string): boolean => {
    const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
    const hostnameRegex = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
    return ipRegex.test(value) || hostnameRegex.test(value);
  };

  const validatePort = (value: string): boolean => {
    const port = parseInt(value);
    return !isNaN(port) && port > 0 && port <= 65535;
  };

  const handleInputChange = (field: keyof SSHCredentials, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));

    if (value.length > 0) {
      let isValid = false;
      switch (field) {
        case 'hostname':
          isValid = validateHostname(value);
          break;
        case 'port':
          isValid = validatePort(value);
          break;
        case 'username':
          isValid = value.length >= 3;
          break;
        case 'password':
          isValid = value.length >= 6;
          break;
      }
      setValidation(prev => ({ ...prev, [field]: isValid }));
    } else {
      setValidation(prev => ({ ...prev, [field]: null }));
    }
  };

  const handleConnect = async () => {
    const allValid =
      validateHostname(formData.hostname) &&
      validatePort(formData.port) &&
      formData.username.length >= 3 &&
      formData.password.length >= 6;

    if (!allValid) {
      setValidation({
        hostname: validateHostname(formData.hostname),
        port: validatePort(formData.port),
        username: formData.username.length >= 3,
        password: formData.password.length >= 6,
      });
      return;
    }

    await onConnect(formData);
  };

  const getInputClassName = (field: keyof ValidationState) => {
    const baseClass = "pl-10 pr-10 transition-all duration-300 bg-background/50 backdrop-blur-sm border-border/50 focus:border-primary/50 focus:bg-background/70";
    if (validation[field] === null) return baseClass;
    return validation[field]
      ? `${baseClass} border-green-500/50 focus:border-green-500/70`
      : `${baseClass} border-red-500/50 focus:border-red-500/70`;
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 bg-slate-950 relative overflow-hidden">
      <BGPattern
        variant="dots"
        mask="fade-edges"
        fill="rgba(139, 92, 246, 0.15)"
        size={32}
      />

      <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-slate-950 to-blue-900/20" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative w-full max-w-md"
      >
        <div className="relative">
          <GlowEffect
            colors={['#8B5CF6', '#3B82F6', '#06B6D4', '#8B5CF6']}
            mode="rotate"
            blur="stronger"
            duration={8}
            className="rounded-2xl"
          />

          <div className="relative bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-slate-800/50 shadow-2xl overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 via-transparent to-blue-500/5" />

            <div className="relative p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-purple-500/30">
                  <Server className="w-6 h-6 text-purple-400" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-white">SSH Connection</h2>
                  <p className="text-sm text-slate-400">Secure Shell Protocol</p>
                </div>
              </div>

              <div className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="hostname" className="text-slate-300 flex items-center gap-2">
                    <span className="text-lg">🌐</span>
                    Hostname / IP Address
                  </Label>
                  <div className="relative">
                    <Server className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                      id="hostname"
                      type="text"
                      placeholder="192.168.1.100 or example.com"
                      value={formData.hostname}
                      onChange={(e) => handleInputChange('hostname', e.target.value)}
                      className={getInputClassName('hostname')}
                      disabled={isConnecting}
                    />
                    {validation.hostname !== null && (
                      <div className="absolute right-3 top-1/2 -translate-y-1/2">
                        {validation.hostname ? (
                          <CheckCircle2 className="w-4 h-4 text-green-500" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-red-500" />
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="port" className="text-slate-300 flex items-center gap-2">
                    <span className="text-lg">🔌</span>
                    Port Number
                  </Label>
                  <div className="relative">
                    <Hash className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                      id="port"
                      type="text"
                      placeholder="22"
                      value={formData.port}
                      onChange={(e) => handleInputChange('port', e.target.value)}
                      className={getInputClassName('port')}
                      disabled={isConnecting}
                    />
                    {validation.port !== null && (
                      <div className="absolute right-3 top-1/2 -translate-y-1/2">
                        {validation.port ? (
                          <CheckCircle2 className="w-4 h-4 text-green-500" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-red-500" />
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="username" className="text-slate-300 flex items-center gap-2">
                    <span className="text-lg">👤</span>
                    Username
                  </Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                      id="username"
                      type="text"
                      placeholder="root"
                      value={formData.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      className={getInputClassName('username')}
                      disabled={isConnecting}
                    />
                    {validation.username !== null && (
                      <div className="absolute right-3 top-1/2 -translate-y-1/2">
                        {validation.username ? (
                          <CheckCircle2 className="w-4 h-4 text-green-500" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-red-500" />
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password" className="text-slate-300 flex items-center gap-2">
                    <span className="text-lg">🔐</span>
                    Password
                  </Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      placeholder="••••••••"
                      value={formData.password}
                      onChange={(e) => handleInputChange('password', e.target.value)}
                      className={getInputClassName('password')}
                      disabled={isConnecting}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-300 transition-colors"
                      disabled={isConnecting}
                    >
                      {showPassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                <motion.div
                  whileHover={{ scale: isConnecting ? 1 : 1.02 }}
                  whileTap={{ scale: isConnecting ? 1 : 0.98 }}
                >
                  <Button
                    onClick={handleConnect}
                    disabled={isConnecting}
                    className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-semibold py-6 rounded-lg shadow-lg shadow-purple-500/25 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isConnecting ? (
                      <span className="flex items-center gap-2">
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                          className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
                        />
                        Connecting...
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <span className="text-lg">🚀</span>
                        Connect to Server
                      </span>
                    )}
                  </Button>
                </motion.div>
              </div>

              <div className="mt-6 pt-6 border-t border-slate-800/50">
                <p className="text-xs text-slate-500 text-center">
                  🔒 Your connection is encrypted and secure
                </p>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};
