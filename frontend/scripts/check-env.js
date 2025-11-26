#!/usr/bin/env node
/**
 * Script para verificar configuração de ambiente antes do deploy
 *
 * Usage: node scripts/check-env.js
 */

const fs = require('fs');
const path = require('path');

console.log('🔍 Verificando configuração de ambiente...\n');

// Carrega .env.production
const envPath = path.join(__dirname, '..', '.env.production');
let hasErrors = false;

if (!fs.existsSync(envPath)) {
  console.error('❌ Arquivo .env.production não encontrado!');
  process.exit(1);
}

const envContent = fs.readFileSync(envPath, 'utf-8');
const lines = envContent.split('\n');

// Verifica REACT_APP_BACKEND_URL
const backendUrlLine = lines.find(line => line.trim().startsWith('REACT_APP_BACKEND_URL='));

if (!backendUrlLine) {
  console.warn('⚠️  REACT_APP_BACKEND_URL não encontrado em .env.production');
  console.warn('   Certifique-se de configurar no Railway!');
  hasErrors = true;
} else {
  const url = backendUrlLine.split('=')[1]?.trim().replace(/["']/g, '');

  console.log(`✅ REACT_APP_BACKEND_URL encontrado: ${url}`);

  // Verifica se usa sintaxe inválida do Railway
  if (url && url.includes('${{')) {
    console.error('❌ ERRO: URL usa sintaxe ${{...}} do Railway!');
    console.error('   Isso NÃO funciona em variáveis REACT_APP_*');
    console.error('   Use URL hardcoded ou configure diretamente no Railway');
    hasErrors = true;
  }

  // Verifica protocolo
  if (url && !url.startsWith('https://')) {
    if (url.startsWith('http://')) {
      if (!url.includes('localhost') && !url.includes('127.0.0.1')) {
        console.error('❌ ERRO: URL usa HTTP em vez de HTTPS!');
        console.error('   Produção DEVE usar HTTPS para evitar Mixed Content');
        hasErrors = true;
      }
    } else {
      console.warn('⚠️  URL sem protocolo - será adicionado automaticamente');
    }
  } else if (url) {
    console.log('✅ Protocolo HTTPS correto');
  }

  // Verifica se é URL interna do Railway
  if (url && url.includes('.railway.internal')) {
    console.error('❌ ERRO: URL usa domínio .railway.internal!');
    console.error('   Isso NÃO funciona do browser');
    console.error('   Use PUBLIC_DOMAIN em vez de PRIVATE_DOMAIN');
    hasErrors = true;
  }
}

// Verifica outras variáveis importantes
const requiredVars = [
  'REACT_APP_APP_NAME',
  'REACT_APP_VERSION'
];

requiredVars.forEach(varName => {
  const line = lines.find(l => l.trim().startsWith(`${varName}=`));
  if (line) {
    console.log(`✅ ${varName} configurado`);
  } else {
    console.warn(`⚠️  ${varName} não encontrado`);
  }
});

// Verifica otimizações de build
const buildVars = {
  'GENERATE_SOURCEMAP': 'false',
  'INLINE_RUNTIME_CHUNK': 'false'
};

console.log('\n📦 Verificando otimizações de build:');
Object.entries(buildVars).forEach(([varName, expectedValue]) => {
  const line = lines.find(l => l.trim().startsWith(`${varName}=`));
  if (line) {
    const value = line.split('=')[1]?.trim();
    if (value === expectedValue) {
      console.log(`✅ ${varName}=${value}`);
    } else {
      console.warn(`⚠️  ${varName}=${value} (recomendado: ${expectedValue})`);
    }
  }
});

console.log('\n' + '='.repeat(60));

if (hasErrors) {
  console.error('\n❌ Encontrados erros na configuração!');
  console.error('   Corrija antes de fazer deploy.\n');
  process.exit(1);
} else {
  console.log('\n✅ Configuração parece OK!');
  console.log('   Lembre-se de configurar variáveis no Railway também.\n');
  process.exit(0);
}
