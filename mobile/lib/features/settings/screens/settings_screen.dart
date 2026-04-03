import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api_client.dart';
import '../../auth/providers/auth_provider.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  final _urlCtrl = TextEditingController();
  bool _testing = false;
  String? _testResult;

  @override
  void initState() {
    super.initState();
    _loadUrl();
  }

  Future<void> _loadUrl() async {
    final api = ref.read(apiClientProvider);
    final url = await api.getServerUrl();
    _urlCtrl.text = url;
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Server connection
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Server Connection',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                          )),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _urlCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Server URL',
                      hintText: 'http://192.168.1.x:8000',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.dns_outlined),
                      helperText:
                          'Use local IP when connecting from your phone over WiFi',
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      OutlinedButton.icon(
                        onPressed: _testing ? null : _testConnection,
                        icon: _testing
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.wifi_outlined, size: 16),
                        label: const Text('Test'),
                      ),
                      const SizedBox(width: 8),
                      FilledButton.tonal(
                        onPressed: _saveUrl,
                        child: const Text('Save'),
                      ),
                    ],
                  ),
                  if (_testResult != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      _testResult!,
                      style: TextStyle(
                        color: _testResult!.startsWith('✓')
                            ? Colors.green
                            : Colors.red,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),

          const SizedBox(height: 16),

          // Account
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Account',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                          )),
                  const SizedBox(height: 12),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const CircleAvatar(child: Icon(Icons.person)),
                    title: Text(authState.username ?? 'User'),
                    subtitle: const Text('Logged in'),
                    trailing: TextButton(
                      onPressed: _logout,
                      child: const Text('Logout',
                          style: TextStyle(color: Colors.red)),
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 16),

          // About
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('About',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                          )),
                  const SizedBox(height: 8),
                  const _InfoRow('App', 'ApplyCopilot v1.0.0'),
                  const _InfoRow('License', 'MIT'),
                  const _InfoRow(
                      'Source', 'github.com/Uni-coder-harsh/ApplyCopilot'),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _testConnection() async {
    setState(() { _testing = true; _testResult = null; });
    await _saveUrl();
    final api = ref.read(apiClientProvider);
    final ok = await api.checkHealth();
    setState(() {
      _testing = false;
      _testResult = ok ? '✓ Connected successfully' : '✗ Could not connect — is the server running?';
    });
  }

  Future<void> _saveUrl() async {
    final api = ref.read(apiClientProvider);
    await api.saveServerUrl(_urlCtrl.text.trim());
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Server URL saved')),
      );
    }
  }

  void _logout() {
    ref.read(authProvider.notifier).logout();
    context.go('/login');
  }

  @override
  void dispose() {
    _urlCtrl.dispose();
    super.dispose();
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow(this.label, this.value, {super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 80,
            child: Text(label,
                style: TextStyle(
                    color: Theme.of(context).colorScheme.onSurfaceVariant)),
          ),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}
