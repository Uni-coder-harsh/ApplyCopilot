import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/screens/login_screen.dart';
import '../features/dashboard/screens/dashboard_screen.dart';
import '../features/applications/screens/applications_screen.dart';
import '../features/applications/screens/application_detail_screen.dart';
import '../features/profile/screens/profile_screen.dart';
import '../features/skills/screens/skills_screen.dart';
import '../features/resume/screens/resume_screen.dart';
import '../features/settings/screens/settings_screen.dart';
import '../features/auth/providers/auth_provider.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/dashboard',
    redirect: (context, state) {
      final isLoggedIn = authState.token != null;
      final isLoginRoute = state.matchedLocation == '/login' ||
          state.matchedLocation == '/setup';

      if (!isLoggedIn && !isLoginRoute) return '/login';
      if (isLoggedIn && isLoginRoute) return '/dashboard';
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (_, __) => const LoginScreen(),
      ),
      ShellRoute(
        builder: (context, state, child) => ScaffoldWithNav(child: child),
        routes: [
          GoRoute(
            path: '/dashboard',
            builder: (_, __) => const DashboardScreen(),
          ),
          GoRoute(
            path: '/applications',
            builder: (_, __) => const ApplicationsScreen(),
            routes: [
              GoRoute(
                path: ':id',
                builder: (_, state) => ApplicationDetailScreen(
                  appId: int.parse(state.pathParameters['id']!),
                ),
              ),
            ],
          ),
          GoRoute(
            path: '/profile',
            builder: (_, __) => const ProfileScreen(),
          ),
          GoRoute(
            path: '/skills',
            builder: (_, __) => const SkillsScreen(),
          ),
          GoRoute(
            path: '/resume',
            builder: (_, __) => const ResumeScreen(),
          ),
          GoRoute(
            path: '/settings',
            builder: (_, __) => const SettingsScreen(),
          ),
        ],
      ),
    ],
  );
});

class ScaffoldWithNav extends StatelessWidget {
  final Widget child;
  const ScaffoldWithNav({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;

    final destinations = [
      (path: '/dashboard',    icon: Icons.dashboard_outlined,  label: 'Dashboard'),
      (path: '/applications', icon: Icons.work_outline,         label: 'Jobs'),
      (path: '/resume',       icon: Icons.description_outlined, label: 'Resume'),
      (path: '/skills',       icon: Icons.psychology_outlined,  label: 'Skills'),
      (path: '/profile',      icon: Icons.person_outline,       label: 'Profile'),
    ];

    int currentIndex = destinations.indexWhere(
      (d) => location.startsWith(d.path),
    );
    if (currentIndex < 0) currentIndex = 0;

    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: (i) => context.go(destinations[i].path),
        destinations: destinations
            .map((d) => NavigationDestination(
                  icon: Icon(d.icon),
                  label: d.label,
                ))
            .toList(),
      ),
    );
  }
}
