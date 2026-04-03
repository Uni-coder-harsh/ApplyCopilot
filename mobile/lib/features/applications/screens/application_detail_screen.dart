import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../providers/applications_provider.dart';
import '../../../core/api_client.dart';

class ApplicationDetailScreen extends ConsumerWidget {
  final int appId;
  const ApplicationDetailScreen({super.key, required this.appId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appAsync = ref.watch(applicationDetailProvider(appId));

    return Scaffold(
      appBar: AppBar(title: const Text('Application')),
      body: appAsync.when(
        data: (app) => _DetailView(app: app, ref: ref),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }
}

class _DetailView extends StatelessWidget {
  final Map<String, dynamic> app;
  final WidgetRef ref;
  const _DetailView({required this.app, required this.ref});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Header
        Text(
          app['company'] ?? '',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 4),
        Text(
          app['role'] ?? '',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
        ),

        const SizedBox(height: 16),

        // Match score
        if (app['match_score'] != null)
          _ScoreBar(score: (app['match_score'] as num).toDouble()),

        const SizedBox(height: 16),

        // Details chips
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _InfoChip(label: app['stage'] ?? '', icon: Icons.flag_outlined),
            _InfoChip(label: app['status'] ?? '', icon: Icons.info_outline),
            _InfoChip(label: app['job_type'] ?? '', icon: Icons.category_outlined),
            if (app['remote'] == true)
              _InfoChip(label: 'Remote', icon: Icons.home_work_outlined),
            if (app['location'] != null)
              _InfoChip(label: app['location'], icon: Icons.location_on_outlined),
          ],
        ),

        const SizedBox(height: 24),

        // Dates
        _SectionTitle('Timeline'),
        _InfoRow('Applied', _formatDate(app['applied_date'])),
        _InfoRow('Last updated', _formatDate(app['last_updated'])),
        if (app['followup_date'] != null)
          _InfoRow('Follow-up', _formatDate(app['followup_date'])),

        if (app['notes'] != null && app['notes'].toString().isNotEmpty) ...[
          const SizedBox(height: 16),
          _SectionTitle('Notes'),
          Text(app['notes']),
        ],

        if (app['url'] != null) ...[
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: () => _launchUrl(app['url']),
            icon: const Icon(Icons.open_in_new),
            label: const Text('View job posting'),
          ),
        ],

        const SizedBox(height: 24),

        // Stage update
        _SectionTitle('Update Stage'),
        _StageUpdater(appId: app['id'], currentStage: app['stage'], ref: ref),
      ],
    );
  }

  String _formatDate(String? iso) {
    if (iso == null) return 'N/A';
    try {
      final dt = DateTime.parse(iso);
      return '${dt.day}/${dt.month}/${dt.year}';
    } catch (_) {
      return iso;
    }
  }

  void _launchUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }
}

class _ScoreBar extends StatelessWidget {
  final double score;
  const _ScoreBar({required this.score});

  @override
  Widget build(BuildContext context) {
    final color = score >= 70 ? Colors.green : score >= 40 ? Colors.orange : Colors.red;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Match Score', style: Theme.of(context).textTheme.labelLarge),
            Text(
              '${score.toStringAsFixed(0)}%',
              style: TextStyle(fontWeight: FontWeight.bold, color: color),
            ),
          ],
        ),
        const SizedBox(height: 8),
        LinearProgressIndicator(
          value: score / 100,
          color: color,
          backgroundColor: color.withOpacity(0.15),
          minHeight: 8,
          borderRadius: BorderRadius.circular(4),
        ),
      ],
    );
  }
}

class _InfoChip extends StatelessWidget {
  final String label;
  final IconData icon;
  const _InfoChip({required this.label, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Chip(
      avatar: Icon(icon, size: 16),
      label: Text(label),
      padding: EdgeInsets.zero,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
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
            width: 110,
            child: Text(
              label,
              style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant),
            ),
          ),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String title;
  const _SectionTitle(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(title,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
              )),
    );
  }
}

class _StageUpdater extends StatelessWidget {
  final int appId;
  final String currentStage;
  final WidgetRef ref;

  const _StageUpdater({
    required this.appId,
    required this.currentStage,
    required this.ref,
  });

  static const stages = [
    'cold_email_sent', 'applied', 'awaiting_reply',
    'shortlisted', 'oa', 'interview', 'final_round', 'offer',
  ];

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: stages.map((stage) {
        final isCurrent = stage == currentStage;
        return ChoiceChip(
          label: Text(stage.replaceAll('_', ' ')),
          selected: isCurrent,
          onSelected: isCurrent ? null : (_) => _updateStage(context, stage),
        );
      }).toList(),
    );
  }

  Future<void> _updateStage(BuildContext context, String stage) async {
    final api = ref.read(apiClientProvider);
    await api.updateApplication(appId, {'stage': stage});
    ref.invalidate(applicationDetailProvider(appId));
    ref.invalidate(applicationsProvider);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Stage updated to $stage')),
      );
    }
  }
}
