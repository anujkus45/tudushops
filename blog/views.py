from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from .models import Post, Comment, Category
from .forms import PostForm, CommentForm

class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        # Optimization: select_related handles foreign key (author), prefetch_related handles many-to-many (categories)
        queryset = Post.objects.filter(is_published=True).select_related('author').prefetch_related('categories')
        
        # Intercept search query parameter 'q'
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(content__icontains=query)
            ).distinct()
            
        return queryset

class CategoryPostListView(PostListView):
    # We can reuse the post_list template and just pass different context
    template_name = 'blog/post_list.html'

    def get_queryset(self):
        # Call super() to keep the search logic and query optimizations intact
        queryset = super().get_queryset()
        category_slug = self.kwargs.get('slug')
        # Get category or return 404
        self.category = get_object_or_404(Category, slug=category_slug)
        # Filter posts by the specific category
        return queryset.filter(categories=self.category)

    def get_context_data(self, **kwargs):
        # Inject the category into the template to display "Viewing category: X"
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context

class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    
    # We use slug pattern for clean URLs naturally
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        # Optimization: prefetch_related caches all comments and their deeply nested authors!
        return Post.objects.filter(is_published=True).select_related('author').prefetch_related(
            'categories', 
            'comments__author'
        )

    def get_context_data(self, **kwargs):
        # Inject the CommentForm into the detail view context so it can be rendered
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CommentForm()
        return context

class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm

    def form_valid(self, form):
        post = get_object_or_404(Post, slug=self.kwargs.get('slug'))
        form.instance.author = self.request.user
        form.instance.post = post
        messages.success(self.request, '💬 Comment posted successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, '❌ Comment could not be posted. Please try again.')
        return redirect('post-detail', slug=self.kwargs.get('slug'))

    def get_success_url(self):
        return reverse_lazy('post-detail', kwargs={'slug': self.kwargs['slug']})

class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'🎉 Post "{self.object.title}" published successfully!')
        return response

    def form_invalid(self, form):
        messages.error(self.request, '❌ Could not publish post. Please fix the errors below.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('post-detail', kwargs={'slug': self.object.slug})

class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'✏️ Post "{self.object.title}" updated successfully!')
        return response

    def form_invalid(self, form):
        messages.error(self.request, '❌ Could not update post. Please fix the errors below.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('post-detail', kwargs={'slug': self.object.slug})

    def test_func(self):
        # Ensure only the author can edit the post
        post = self.get_object()
        return self.request.user == post.author


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'blog/post_confirm_delete.html'
    success_url = reverse_lazy('post-list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def delete(self, request, *args, **kwargs):
        post = self.get_object()
        messages.success(request, f'🗑️ Post "{post.title}" deleted successfully.')
        return super().delete(request, *args, **kwargs)

    def test_func(self):
        post = self.get_object()
        if self.request.user != post.author:
            messages.error(self.request, '🚫 You are not allowed to delete this post.')
            return False
        return True

