from typing import Any, Generic, Type, TypeVar

from fastapi import APIRouter, BackgroundTasks, Request

from core.exceptions import BaseHTTPException
from server.config import Settings

# from .handlers import create_dto
from .models import BaseEntity, ## TaskBaseEntity


"""
Based on models developed in app>apps>base>models.py
write CRUP Endpoints with maturity level 2
"""

#### Invoice Endpoints ####

##### list of invoices #####
@router.get("/invoice")
async def get_invoices(
    request: Request,
    business_id: uuid.UUID,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
    is_deleted: Optional[bool] = False,
    merchant: Optional[str] = None,
    customer: Optional[str] = None,
    proposal_id: Optional[str] = None,
    transaction_id: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    currency: Optional[str] = None,
    status: Optional[str] = None,
    due_date: Optional[datetime] = None,
    issued_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """
    Retuen list of invoices.

    Requiered parameter:
        business_id
    Optional:
        created_at
        updated_at
        is_deleted
        merchant
        customer
        proposal_id
        transaction_id
        user_id
        currency
        status
        due_date
        issued_date
    """
    try:
        query = db.query(models.Invoice).filter(models.Invoice.business_id == business_id)
        if created_at:
            query = query.filter(models.Invoice.created_at == created_at)
        if updated_at:
            query = query.filter(models.Invoice.updated_at == updated_at)
        if is_deleted:
            query = query.filter(models.Invoice.is_deleted == is_deleted)
        if merchant:
            query = query.filter(models.Invoice.merchant == merchant)
        if customer:
            query = query.filter(models.Invoice.customer == customer)
        if proposal_id:
            query = query.filter(models.Invoice.proposal_id == proposal_id)
        if transaction_id:
            query = query.filter(models.Invoice.transaction_id == transaction_id)
        if user_id:
            query = query.filter(models.Invoice.user_id == user_id)
        if currency:
            query = query.filter(models.Invoice.currency == currency)
        if status:
            query = query.filter(models.Invoice.status == status)
        if due_date:
            query = query.filter(models.Invoice.due_date == due_date)
        if issued_date:
            query = query.filter(models.Invoice.issued_date == issued_date)

        invoices = query.all()
        if not invoices:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoices not found",
            )
        return invoices
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}",
        )

##### return single invoice #####

@router.get("/invoice/{uid}", response_model=schemas.Invoice)
async def get_invoice(
    uid: uuid.UUID,
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """ return single invoice """
    try:
        invoice = db.query(models.Invoice).filter(models.Invoice.uid == uid).first()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found",
            )

        if invoice.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice does not belong to the business",
            )

        return invoice

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}",
        )

##### create an Invoice #####

@router.post("/invoice", response_model=schemas.Invoice)
async def create_invoice(
    *,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    is_deleted: bool = False,
    merchant: dict,
    customer: dict,
    proposal_id: str,
    transaction_id: str,
    currency: str,
    status: str,
    due_date: datetime,
    issued_date: datetime,
    db: Session = Depends(get_db),
):
    """
    Create an Invoice.

    Requiered parameter:
        business_id
        user_id
        merchant
        customer
        proposal_id
        transaction_id
        currency
        status
        due_date
        issued_date
    """
    try:
        invoice = models.Invoice(
            business_id=business_id,
            user_id=user_id,
            is_deleted=is_deleted,
            merchant=merchant,
            customer=customer,
            proposal_id=proposal_id,
            transaction_id=transaction_id,
            currency=currency,
            status=status,
            due_date=due_date,
            issued_date=issued_date,
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        return invoice

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}",
        )
#### update an Invoice #####

@router.put("/invoice/{uid}", response_model=schemas.Invoice)
async def update_invoice(
    *,
    uid: uuid.UUID,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    is_deleted: bool,
    merchant: dict,
    customer: dict,
    proposal_id: str,
    transaction_id: str,
    currency: str,
    status: str,
    due_date: datetime,
    issued_date: datetime,
    db: Session = Depends(get_db),
):
    """
    Update an Invoice.

    Required parameter:
        uid
        business_id
        user_id
        is_deleted
        merchant
        customer
        proposal_id
        transaction_id
        currency
        status
        due_date
        issued_date
    """

    try:
        # get invoice by uid
        invoice = db.query(models.Invoice).filter_by(uid=uid).first()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice with uid {uid} not found",
            )

        # update invoice
        invoice.business_id = business_id
        invoice.user_id = user_id
        invoice.is_deleted = is_deleted
        invoice.merchant = merchant
        invoice.customer = customer
        invoice.proposal_id = proposal_id
        invoice.transaction_id = transaction_id
        invoice.currency = currency
        invoice.status = status
        invoice.due_date = due_date
        invoice.issued_date = issued_date
        db.commit()
        db.refresh(invoice)
        return invoice

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}",
        )


#### delete an Invoice #####

@router.delete("/invoice/{uid}", response_model=schemas.Invoice)
async def delete_invoice(
    uid: uuid.UUID,
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Delete an Invoice.

    Required parameters:
        business_id
        uid
    """
    try:
        # get invoice by uid
        invoice = db.query(models.Invoice).filter_by(uid=uid).first()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice with uid {uid} not found",
            )

        # update invoice
        if invoice.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice does not belong to the business",
            )

        invoice.is_deleted = True
        db.commit()
        db.refresh(invoice)
        return invoice

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}",
        )

#### End of Invoice ####

#### revenue sharing rules Endpoints ####

##### return list of revenue sharing rules #####

@router.get("/revenue_sharing_rule")
async def get_revenue_sharing_rules(
    business_id: uuid.UUID,
    name: Optional[str] = None,
    is_default: Optional[bool] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """return list of revenue sharing rules"""
    try:
        query = db.query(models.RevenueSharingRule).filter_by(
            business_id=business_id
        )
        if name:
            query = query.filter_by(name=name)
        if is_default is not None:
            query = query.filter_by(is_default=is_default)
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        return query.all()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,


##### return single revenue sharing rule #####

@router.get("/revenue_sharing_rule/{uid}", response_model=models.RevenueSharingRule)
async def get_revenue_sharing_rule(
    uid: uuid.UUID,
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """ return single revenue sharing rule """
    try:
        rule = db.query(models.RevenueSharingRule).filter_by(uid=uid).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Revenue Sharing Rule not found",
            )

        if rule.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Revenue Sharing Rule does not belong to the business",
            )

        return rule

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}",
        )

##### Create a Revenue Sharing Rule #####
@router.post("/revenue_sharing_rule", response_model=models.RevenueSharingRule)
async def create_revenue_sharing_rule(
    business_id: uuid.UUID,
    name: str,
    description: Optional[str] = None,
    is_default: bool,
    is_active: bool,
    shares: list[dict],
    db: Session = Depends(get_db),
):
    """
    Create a Revenue Sharing Rule.

    Required parameters:
        business_id
        name
        description
        is_default
        is_active
        shares
    """
    try:
        rule = models.RevenueSharingRule(
            business_id=business_id,
            name=name,
            description=description,
            is_default=is_default,
            is_active=is_active,
            shares=shares,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}",
        )

### update a revenue sharing rule #####
@router.put("/revenue_sharing_rule/{uid}", response_model=models.RevenueSharingRule)
async def update_revenue_sharing_rule(
    uid: uuid.UUID,
    business_id: uuid.UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_default: Optional[bool] = None,
    is_active: Optional[bool] = None,
    shares: Optional[list[dict]] = None,
    db: Session = Depends(get_db),
):
    """
    Update a Revenue Sharing Rule.

    Required parameters:
        uid
        business_id
    Optional parameters:
        name
        description
        is_default
        is_active
        shares
    """
    try:
        rule = db.query(models.RevenueSharingRule).filter_by(uid=uid).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Revenue Sharing Rule not found",
            )

        if rule.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Revenue Sharing Rule does not belong to the business",
            )

        if name:
            rule.name = name
        if description:
            rule.description = description
        if is_default is not None:
            rule.is_default = is_default
        if is_active is not None:
            rule.is_active = is_active
        if shares:
            rule.shares = shares
        db.commit()
        db.refresh(rule)
        return rule

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}",
        )

##### delete a revenue sharing rule #####



@router.delete("/revenue_sharing_rule/{uid}", response_model=models.RevenueSharingRule)
async def delete_revenue_sharing_rule(
    uid: uuid.UUID,
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Delete a Revenue Sharing Rule.

    Required parameters:
        business_id
        uid
    """
    try:
        # get revenue sharing rule by uid
        rule = db.query(models.RevenueSharingRule).filter_by(uid=uid).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Revenue Sharing Rule not found",
            )

        # update invoice
        if rule.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Revenue Sharing Rule does not belong to the business",
            )

        rule.is_active = False
        db.commit()
        db.refresh(rule)
        return rule

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}",
        )
