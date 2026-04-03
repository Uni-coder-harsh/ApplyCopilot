import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/skills_provider.dart';

class SkillsScreen extends ConsumerWidget {
  const SkillsScreen({super.key});

  static const _categoryColors = {
    'programming': Colors.blue,
    'ml':          Colors.purple,
    'devops':      Colors.teal,
    'research':    Colors.orange,
    'tools':       Colors.green,
    'other':       Colors.grey,
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final skillsAsync = ref.watch(skillsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Skills'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_outlined),
            onPressed: () => ref.invalidate(skillsProvider),
          ),
        ],
      ),
      body: skillsAsync.when(
        data: (skills) {
          if (skills.isEmpty) {
            return const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.psychology_outlined, size: 64, color: Colors.grey),
                  SizedBox(height: 16),
                  Text('No skills yet'),
                  SizedBox(height: 8),
                  Text(
                    'Run applycopilot skills scan on your computer',
                    style: TextStyle(color: Colors.grey),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            );
          }

          // Group by category
          final grouped = <String, List<Map<String, dynamic>>>{};
          for (final skill in skills) {
            final cat = skill['category'] as String? ?? 'other';
            grouped.putIfAbsent(cat, () => []).add(skill as Map<String, dynamic>);
          }

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(skillsProvider),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: grouped.entries.map((entry) {
                final color = _categoryColors[entry.key] ?? Colors.grey;
                return _SkillCategory(
                  category: entry.key,
                  skills: entry.value,
                  color: color,
                );
              }).toList(),
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }
}

class _SkillCategory extends StatelessWidget {
  final String category;
  final List<Map<String, dynamic>> skills;
  final Color color;

  const _SkillCategory({
    required this.category,
    required this.skills,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 10, top: 16),
          child: Row(
            children: [
              Container(
                width: 4,
                height: 16,
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                category.toUpperCase(),
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: color,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.5,
                    ),
              ),
            ],
          ),
        ),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: skills.map((skill) => _SkillChip(skill: skill, color: color)).toList(),
        ),
      ],
    );
  }
}

class _SkillChip extends StatelessWidget {
  final Map<String, dynamic> skill;
  final Color color;

  const _SkillChip({required this.skill, required this.color});

  @override
  Widget build(BuildContext context) {
    final confidence = (skill['confidence'] as num?)?.toDouble() ?? 0.7;
    final opacity = 0.1 + confidence * 0.2;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(opacity),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            skill['name'] ?? '',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w500,
              color: color.withOpacity(0.9 + confidence * 0.1),
            ),
          ),
          if (skill['level'] != null) ...[
            const SizedBox(width: 4),
            Text(
              '· ${skill['level']}',
              style: TextStyle(
                fontSize: 11,
                color: color.withOpacity(0.7),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
