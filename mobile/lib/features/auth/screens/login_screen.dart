import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api_client.dart';
import '../providers/auth_provider.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _urlCtrl = TextEditingController();
  bool _obscurePassword = true;
  bool _showAdvanced = false;

  @override
  void initState() {
    super.initState();
    _loadServerUrl();
  }

  Future<void> _loadServerUrl() async {
    final api = ref.read(apiClientProvider);
    final url = await api.getServerUrl();
    _urlCtrl.text = url;
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 32),

                  // Logo + title
                  Icon(Icons.rocket_launch_rounded,
                      size: 48, color: colorScheme.primary),
                  const SizedBox(height: 16),
                  Text(
                    'ApplyCopilot',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Your local AI job tracker',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                  ),

                  const SizedBox(height: 40),

                  // Username
                  TextField(
                    controller: _usernameCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Username',
                      prefixIcon: Icon(Icons.person_outline),
                      border: OutlineInputBorder(),
                    ),
                    textInputAction: TextInputAction.next,
                  ),
                  const SizedBox(height: 16),

                  // Password
                  TextField(
                    controller: _passwordCtrl,
                    obscureText: _obscurePassword,
                    decoration: InputDecoration(
                      labelText: 'Password',
                      prefixIcon: const Icon(Icons.lock_outline),
                      border: const OutlineInputBorder(),
                      suffixIcon: IconButton(
                        icon: Icon(_obscurePassword
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined),
                        onPressed: () =>
                            setState(() => _obscurePassword = !_obscurePassword),
                      ),
                    ),
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _login(),
                  ),

                  const SizedBox(height: 8),

                  // Advanced: server URL
                  TextButton.icon(
                    onPressed: () => setState(() => _showAdvanced = !_showAdvanced),
                    icon: Icon(_showAdvanced
                        ? Icons.expand_less
                        : Icons.expand_more),
                    label: const Text('Server settings'),
                  ),

                  if (_showAdvanced) ...[
                    const SizedBox(height: 8),
                    TextField(
                      controller: _urlCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Server URL',
                        hintText: 'http://192.168.1.x:8000',
                        prefixIcon: Icon(Icons.wifi_outlined),
                        border: OutlineInputBorder(),
                        helperText:
                            'Use local IP when connecting from your phone',
                      ),
                    ),
                    const SizedBox(height: 8),
                  ],

                  // Error message
                  if (authState.error != null) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: colorScheme.errorContainer,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.error_outline,
                              color: colorScheme.onErrorContainer, size: 18),
                          const SizedBox(width: 8),
                          Text(
                            authState.error!,
                            style: TextStyle(color: colorScheme.onErrorContainer),
                          ),
                        ],
                      ),
                    ),
                  ],

                  const SizedBox(height: 24),

                  // Login button
                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: FilledButton(
                      onPressed: authState.isLoading ? null : _login,
                      child: authState.isLoading
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Sign in'),
                    ),
                  ),

                  const SizedBox(height: 24),

                  Text(
                    'Make sure applycopilot server is running on your computer.',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _login() async {
    if (_urlCtrl.text.isNotEmpty) {
      final api = ref.read(apiClientProvider);
      await api.saveServerUrl(_urlCtrl.text);
    }

    final success = await ref.read(authProvider.notifier).login(
          _usernameCtrl.text.trim(),
          _passwordCtrl.text,
        );

    if (success && mounted) {
      context.go('/dashboard');
    }
  }

  @override
  void dispose() {
    _usernameCtrl.dispose();
    _passwordCtrl.dispose();
    _urlCtrl.dispose();
    super.dispose();
  }
}
