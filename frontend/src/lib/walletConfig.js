import { connectorsForWallets } from '@rainbow-me/rainbowkit';
import { coinbaseWallet, injectedWallet, rainbowWallet, walletConnectWallet } from '@rainbow-me/rainbowkit/wallets';
import { createConfig, http } from 'wagmi';
import { defineChain } from 'viem';
import { metaMaskInjectedWallet } from './metaMaskInjectedWallet';

const projectId = process.env.REACT_APP_WALLETCONNECT_PROJECT_ID;
const chainId = Number(process.env.REACT_APP_ROBINHOOD_CHAIN_ID);
const rpcUrl = process.env.REACT_APP_ROBINHOOD_RPC_URL;
const explorerUrl = process.env.REACT_APP_ROBINHOOD_EXPLORER_URL;
const appUrl = process.env.REACT_APP_BACKEND_URL;

if (!rpcUrl || !explorerUrl || !appUrl || chainId !== 4663) {
  throw new Error('Wallet configuration requires Robinhood Mainnet (4663) environment settings.');
}

export const robinhoodMainnet = defineChain({
  id: chainId,
  name: 'Robinhood Chain',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: { default: { http: [rpcUrl] } },
  blockExplorers: { default: { name: 'Robinhood Explorer', url: explorerUrl } },
});

// Always let RainbowKit populate rkDetails, including for injected-only mode.
// Calling injectedWallet().createConnector({}) crashes when an extension exists.
const connectors = connectorsForWallets(projectId ? [
  { groupName: 'Wallets', wallets: [metaMaskInjectedWallet, rainbowWallet, coinbaseWallet, walletConnectWallet] },
  { groupName: 'Browser wallets', wallets: [injectedWallet] },
] : [{ groupName: 'Browser wallets', wallets: [injectedWallet] }],
{ appName: 'LastZHood', appUrl, projectId });

export const wagmiConfig = createConfig({
  chains: [robinhoodMainnet],
  connectors,
  transports: { [robinhoodMainnet.id]: http(rpcUrl) },
  multiInjectedProviderDiscovery: true,
  ssr: false,
});