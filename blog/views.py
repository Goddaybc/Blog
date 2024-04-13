from .models import Post
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .forms import EmailPostForm,CommentForm
from django.views.decorators.http import require_POST

from django.core.mail import send_mail
from taggit.models import Tag

from django.db.models import Count

from django.contrib.postgres.search import SearchVector
from .forms import EmailPostForm,CommentForm,SearchForm

# from django.contrib.postgres.search import SearchVector,\
    # SearchQuery,SearchRank


from django.contrib.postgres.search import TrigramSimilarity

def post_list(request, tag_slug=None):
    post_list = Post.objects.filter(status=Post.Status.PUBLISHED)
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])
    # Pagination with 3 posts per page
    paginator = Paginator(post_list, 3)
    page_number = request.GET.get('page', 1)
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        # If page_number is not an integer deliver the first page
        posts = paginator.page(1)
    except EmptyPage:
        # If page_number is out of range deliver last page of results
        posts = paginator.page(paginator.num_pages)
    return render(request,
                 'blog/post/list.html',
                 {'posts': posts,
                  'tag': tag})

# class PostListView(ListView):
#     """
#     Alternative post list view
#     """
#     queryset = Post.objects.filter(status=Post.Status.PUBLISHED)
#     context_object_name = 'posts'
#     paginate_by = 3
#     template_name = 'blog/post/list.html'


def post_detail(request, year, month, day, post):
    # Retrieve the post using the provided year, month, day, and post slug
    post = get_object_or_404(Post, 
                             publish__year=year,
                             publish__month=month,
                             publish__day=day,
                             slug=post)
    # List of active comments for this post
    comments = post.comments.filter(active=True)
    # Form for users to comment
    form = CommentForm()
    # List of similar posts
    post_queryset = Post.objects.filter(status=Post.Status.PUBLISHED)
    post_tags_id = post.tags.all().values_list('id',flat=True)
    similar_posts = post_queryset.filter(tags__in=post_tags_id)\
        .exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags'))\
        .order_by('-same_tags','-publish')[:4]
    return render(request, 'blog/post/post_detail.html', {'post': post,
                                                          'post_id': post.id,
                                                          'comments':comments,
                                                          'form':form,
                                                          'similar_posts': similar_posts})


def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    sent = False
    if request.method == 'POST':
        # form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Form fields passed validation
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f"{cd.get('name', 'Someone')} recommends you read " \
                f"{post.title}"
            message = f"Read {post.title} at {post_url}\n\n"
            if 'comments' in cd:
                message += f"{cd['name']}'s comments: {cd['comments']}"
            else:
                message += "No comments provided"
            send_mail(subject, message, 'goddayoghenerobiz@gmail.com', [cd['to']])
            sent = True
    else:
        form = EmailPostForm()
        
    return render(request, 'blog/post/share.html', {'post': post,
                                                     'form': form,
                                                     'sent': sent})

@require_POST
def post_comment(request,post_id):
    post = get_object_or_404(Post, id=post_id,status=Post.Status.PUBLISHED)
    comment = None
    # When a comment is posted
    form = CommentForm(data=request.POST)
    if form.is_valid():
        # Create a Comment object without saving it to the database
        comment = form.save(commit=False)
        # Assign the post to the comment
        comment.post = post
        # Save the comment to the database
        comment.save()
    return render(request, 'blog/post/comment.html',{'post':post,
                  'form':form,
                  'comment':comment})
                  
def post_search(request):
    form = SearchForm()
    query = None
    results = []
    
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            # search_vector = SearchVector('title',weight='A')+\
            #     SearchVector('body',weight='B')
            # search_query = SearchQuery(query)
            result_obj = Post.objects.filter(status=Post.Status.PUBLISHED)
            results = result_obj.annotate(similarity=TrigramSimilarity('title',query))\
                .filter(similarity__gte=0.1)\
                    .order_by('-similarity')
                
    return render(request,'blog/post/search.html',{
                  'form': form,
                  'query': query,
                  'results':results})

