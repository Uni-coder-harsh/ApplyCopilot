import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/profile_provider.dart';
import '../../../core/api_client.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(profileProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_outlined),
            onPressed: () => ref.invalidate(profileProvider),
          ),
        ],
      ),
      body: profileAsync.when(
        data: (profile) => _ProfileView(profile: profile),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }
}

class _ProfileView extends ConsumerStatefulWidget {
  final Map<String, dynamic> profile;
  const _ProfileView({required this.profile});

  @override
  ConsumerState<_ProfileView> createState() => _ProfileViewState();
}

class _ProfileViewState extends ConsumerState<_ProfileView> {
  late final Map<String, TextEditingController> _controllers;
  bool _editing = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final p = widget.profile;
    _controllers = {
      'full_name':       TextEditingController(text: p['full_name'] ?? ''),
      'phone':           TextEditingController(text: p['phone'] ?? ''),
      'location':        TextEditingController(text: p['location'] ?? ''),
      'university':      TextEditingController(text: p['university'] ?? ''),
      'degree':          TextEditingController(text: p['degree'] ?? ''),
      'branch':          TextEditingController(text: p['branch'] ?? ''),
      'graduation_year': TextEditingController(text: p['graduation_year']?.toString() ?? ''),
      'cgpa':            TextEditingController(text: p['cgpa']?.toString() ?? ''),
      'bio':             TextEditingController(text: p['bio'] ?? ''),
    };
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.profile;
    final colorScheme = Theme.of(context).colorScheme;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Avatar + name
        Center(
          child: Column(
            children: [
              CircleAvatar(
                radius: 40,
                backgroundColor: colorScheme.primaryContainer,
                child: Text(
                  _initials(p['full_name'] ?? 'U'),
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    color: colorScheme.onPrimaryContainer,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                p['full_name'] ?? 'Your Name',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              Text(
                p['primary_email'] ?? '',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 24),

        // Stats row
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            _StatPill(label: 'Skills', value: p['skills_count']?.toString() ?? '0'),
            _StatPill(label: 'Projects', value: p['projects_count']?.toString() ?? '0'),
          ],
        ),

        const SizedBox(height: 24),

        // Edit button
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Personal Info',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    )),
            TextButton.icon(
              onPressed: () => setState(() => _editing = !_editing),
              icon: Icon(_editing ? Icons.close : Icons.edit_outlined, size: 16),
              label: Text(_editing ? 'Cancel' : 'Edit'),
            ),
          ],
        ),

        const SizedBox(height: 8),

        // Fields
        ..._controllers.entries.map((entry) => _editing
            ? Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: TextField(
                  controller: entry.value,
                  decoration: InputDecoration(
                    labelText: _fieldLabel(entry.key),
                    border: const OutlineInputBorder(),
                    isDense: true,
                  ),
                  keyboardType: entry.key == 'graduation_year' || entry.key == 'cgpa'
                      ? TextInputType.number
                      : TextInputType.text,
                ),
              )
            : _InfoRow(
                label: _fieldLabel(entry.key),
                value: entry.value.text.isEmpty ? '—' : entry.value.text,
              )),

        if (_editing) ...[
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _saving ? null : _save,
              child: _saving
                  ? const SizedBox(
                      width: 18, height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Save changes'),
            ),
          ),
        ],

        const SizedBox(height: 24),

        // Social links
        if ((p['social_links'] as List?)?.isNotEmpty == true) ...[
          Text('Social Links',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  )),
          const SizedBox(height: 8),
          ...(p['social_links'] as List).map((sl) => _InfoRow(
                label: sl['platform'],
                value: sl['url'],
              )),
        ],
      ],
    );
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      final api = ref.read(apiClientProvider);
      final data = <String, dynamic>{};
      for (final entry in _controllers.entries) {
        final val = entry.value.text.trim();
        if (val.isEmpty) continue;
        if (entry.key == 'graduation_year') {
          data[entry.key] = int.tryParse(val);
        } else if (entry.key == 'cgpa') {
          data[entry.key] = double.tryParse(val);
        } else {
          data[entry.key] = val;
        }
      }
      await api.updateProfile(data);
      ref.invalidate(profileProvider);
      setState(() => _editing = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profile updated')),
        );
      }
    } finally {
      setState(() => _saving = false);
    }
  }

  String _initials(String name) {
    final parts = name.trim().split(' ');
    if (parts.length >= 2) return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    return name.isNotEmpty ? name[0].toUpperCase() : 'U';
  }

  String _fieldLabel(String key) {
    const labels = {
      'full_name': 'Full name',
      'phone': 'Phone',
      'location': 'Location',
      'university': 'University',
      'degree': 'Degree',
      'branch': 'Branch / Major',
      'graduation_year': 'Graduation year',
      'cgpa': 'CGPA',
      'bio': 'Bio / Summary',
    };
    return labels[key] ?? key;
  }

  @override
  void dispose() {
    for (final c in _controllers.values) c.dispose();
    super.dispose();
  }
}

class _StatPill extends StatelessWidget {
  final String label;
  final String value;
  const _StatPill({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Text(value,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  )),
          Text(label,
              style: TextStyle(
                  color: Theme.of(context).colorScheme.onSurfaceVariant)),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow({required this.label, required this.value, super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(label,
                style: TextStyle(
                    color: Theme.of(context).colorScheme.onSurfaceVariant)),
          ),
          Expanded(
            child: Text(value,
                style: const TextStyle(fontWeight: FontWeight.w500)),
          ),
        ],
      ),
    );
  }
}
