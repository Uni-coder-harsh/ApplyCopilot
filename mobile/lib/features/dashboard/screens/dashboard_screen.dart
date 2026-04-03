import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api_client.dart';
import '../providers/dashboard_provider.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statsAsync = ref.watch(dashboardStatsProvider);
    final followupsAsync = ref.watch(dueFollowupsProvider);
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_outlined),
            onPressed: () {
              ref.invalidate(dashboardStatsProvider);
              ref.invalidate(dueFollowupsProvider);
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(dashboardStatsProvider);
          ref.invalidate(dueFollowupsProvider);
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Stats cards
            statsAsync.when(
              data: (stats) => _StatsGrid(stats: stats),
              loading: () => const _StatsGridSkeleton(),
              error: (e, _) => _ErrorCard(message: e.toString()),
            ),

            const SizedBox(height: 24),

            // Due follow-ups
            Text(
              'Follow-ups due',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 12),

            followupsAsync.when(
              data: (followups) => followups.isEmpty
                  ? _EmptyCard(
                      icon: Icons.check_circle_outline,
                      message: 'No follow-ups due',
                    )
                  : Column(
                      children: followups
                          .take(5)
                          .map((f) => _FollowupCard(data: f))
                          .toList(),
                    ),
              loading: () => const CircularProgressIndicator(),
              error: (e, _) => _ErrorCard(message: e.toString()),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatsGrid extends StatelessWidget {
  final Map<String, dynamic> stats;
  const _StatsGrid({required this.stats});

  @override
  Widget build(BuildContext context) {
    final items = [
      (label: 'Total', value: stats['total'] ?? 0, color: Colors.blue, icon: Icons.work_outline),
      (label: 'Active', value: stats['active'] ?? 0, color: Colors.green, icon: Icons.pending_outlined),
      (label: 'Interviews', value: stats['interviews'] ?? 0, color: Colors.orange, icon: Icons.record_voice_over_outlined),
      (label: 'Offers', value: stats['offers'] ?? 0, color: Colors.purple, icon: Icons.celebration_outlined),
    ];

    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      childAspectRatio: 1.6,
      children: items.map((item) => _StatCard(
        label: item.label,
        value: item.value,
        color: item.color,
        icon: item.icon,
      )).toList(),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final int value;
  final Color color;
  final IconData icon;

  const _StatCard({
    required this.label,
    required this.value,
    required this.color,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Icon(icon, color: color, size: 24),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value.toString(),
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: color,
                      ),
                ),
                Text(
                  label,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _FollowupCard extends StatelessWidget {
  final Map<String, dynamic> data;
  const _FollowupCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final app = data['application'] as Map<String, dynamic>;
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: const CircleAvatar(child: Icon(Icons.notifications_outlined, size: 18)),
        title: Text(app['company'] ?? ''),
        subtitle: Text(app['role'] ?? ''),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.go('/applications/${app['id']}'),
      ),
    );
  }
}

class _StatsGridSkeleton extends StatelessWidget {
  const _StatsGridSkeleton();

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      childAspectRatio: 1.6,
      children: List.generate(4, (_) => Card(
        child: Container(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceVariant,
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      )),
    );
  }
}

class _EmptyCard extends StatelessWidget {
  final IconData icon;
  final String message;
  const _EmptyCard({required this.icon, required this.message});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Row(
          children: [
            Icon(icon, color: Colors.green),
            const SizedBox(width: 12),
            Text(message),
          ],
        ),
      ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  final String message;
  const _ErrorCard({required this.message});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Text('Error: $message',
            style: TextStyle(color: Theme.of(context).colorScheme.error)),
      ),
    );
  }
}
