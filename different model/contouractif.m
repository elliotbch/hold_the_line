img=imread('ligne.jpg');
%img=rgb2gray(img);
double(img);
figure(1);
colormap gray;
imagesc(img);

[x,y]=select_point(img)
% ajouter le contour 
function [x,y]=select_point(img)

colormap(gray);
x=[];
y=[];

disp(' selection du premier point ');
disp('selection du dernier point');
but=1;

while but==1
    clf
    imagesc(img);
    grid on;
    hold on
    plot(x, y, 'r-', 'linewidth',3);
    plot(x, y ,'b+','linewidth',3);
    axis square 
    [s,t,but]=ginput(1);
x=[x;s];
y=[y;t];

end 
end 

% augmentation du nombre de point 
function[xi,yi]=subdivision(x,y)
N=size(x,1); p=1;
for i =1 ; N-1
% subdivision entre deux sommets 
    h_x=(x(i+1)-x(i))/10;
    h_y=(y(i+1)-y(i))/10;
    for j =1 :10
        xi(p,1)=x(i)+j*h_x;
        yi(p,1)=y(i)+j*h_y;
        p=p+1; 
    end 
end 
%subdivision entre le premier et le dernier 
h_x=( x(N)-x(1) )/ 10;
h_y=( y(N)-y(1) )/ 10;
for j= 1:10 
    xi(p,1)=x(1)+j*h_x;
    yi(p,1)=y(1)+j*h_y;
    p=p+1;
    
    
end 
end 
